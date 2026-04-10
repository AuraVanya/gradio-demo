import os
import boto3
import json
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict
from pydantic import ValidationError
from schemas.acord_schema import ACORD125Schema
import pandas as pd
import time

# Load AWS credentials from .env
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-2")
BUCKET_NAME = "textract-colab-temp-bucket"
INFERENCE_PROFILE_ARN = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Initialize clients
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
textract_client = boto3.client(
    "textract",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# --- ACORD Extractor --- #

def upload_to_s3(file):
    """Uploads PDF to S3 and returns the S3 path"""

    if file is None:
        return None, "No file provided"

    if not hasattr(file, 'name'):
        return None, "Invalid file object"

    try:
        filename = os.path.basename(file.name)
        s3_key = f"uploads/{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        s3_client.upload_file(file.name, BUCKET_NAME, s3_key)
        return s3_key, None # return S3 key and no error
    except Exception as e:
        return None, str(e)

def get_kv_map(s3_key):
    """Start async Textract analysis and poll for results"""

    # Start document analysis
    response = textract_client.start_document_analysis(
        DocumentLocation={
            'S3Object': {
                'Bucket': BUCKET_NAME,
                'Name': s3_key
            }
        },
        FeatureTypes=['FORMS']
    )

    job_id = response['JobId']
    print(f"Started Textract job: {job_id}")

    # Poll for completion
    while True:
        result = textract_client.get_document_analysis(JobId=job_id)
        status = result['JobStatus']

        if status == 'SUCCEEDED':
            print("Textract job completed successfully")
            break
        elif status == 'FAILED':
            raise Exception(f"Textract job failed: {result.get('StatusMessage', 'Unknown error')}")

        print(f"Job status: {status}, waiting...")
        time.sleep(2)

    # Get all pages of results
    blocks = result['Blocks']
    next_token = result.get('NextToken')

    while next_token:
        result = textract_client.get_document_analysis(
            JobId=job_id,
            NextToken=next_token
        )
        blocks.extend(result['Blocks'])
        next_token = result.get('NextToken')

    key_map, value_map, block_map = {}, {}, {}

    for block in blocks:
        block_id = block['Id']
        block_map[block_id] = block
        if block['BlockType'] == "KEY_VALUE_SET":
            if 'KEY' in block['EntityTypes']:
                key_map[block_id] = block
            else:
                value_map[block_id] = block

    return key_map, value_map, block_map

def find_value_block(key_block, value_map):

    if 'Relationships' in key_block:
        for rel in key_block['Relationships']:
            if rel['Type'] == 'VALUE':
                for value_id in rel['Ids']:
                    return value_map.get(value_id)

    return None

def get_text(block, block_map):

    text = ""

    if block and 'Relationships' in block:
        for rel in block['Relationships']:
            if rel['Type'] == 'CHILD':
                for child_id in rel['Ids']:
                    child = block_map[child_id]
                    if child['BlockType'] == 'WORD':
                        text += child['Text'] + " "
                    elif child['BlockType'] == 'SELECTION_ELEMENT' and child['SelectionStatus'] == 'SELECTED':
                        text += "X "

    return text.strip()

def get_kv_relationship(key_map, value_map, block_map):
    """
    Builds a dictionary of key-value pairs with confidence scores.
    Returns format:
    {
        "Key Text": [{"value": "Value Text", "key_confidence": 99.5, "value_confidence": 97.3}, ...]
    }
    """
    kvs = defaultdict(list)
    for block_id, key_block in key_map.items():
        value_block = find_value_block(key_block, value_map)
        key_text = get_text(key_block, block_map)
        value_text = get_text(value_block, block_map)
        key_conf = key_block.get('Confidence', 0)
        value_conf = value_block.get('Confidence', 0) if value_block else 0

        kvs[key_text.strip()].append({
            "value": value_text.strip(),
            "key_confidence": key_conf,
            "value_confidence": value_conf
        })
    return kvs

def get_kv_pairs(kvs):

    kv_pairs = []

    for key, entries in kvs.items():
        for entry in entries:
            kv_pairs.append({
                "key": key,
                "value": entry["value"],
                "key_confidence": entry["key_confidence"],
                "value_confidence": entry["value_confidence"]
            })

    return kv_pairs

# Update your run_bedrock_analysis function
def run_bedrock_analysis(extracted_data, schema):
    text_data = json.dumps(extracted_data, indent=2)
    schema_dump = json.dumps(schema, indent=2)

    print("Transforming and validating extracted data...")

    try:
        response = bedrock_runtime_client.invoke_model(
            modelId=INFERENCE_PROFILE_ARN,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,  # INCREASED from 1000 to handle full response
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": [{
                            "type": "text",
                            "text":  f"""
                                      You are an expert in commercial insurance forms and ACORD document understanding.

                                      **Task:**
                                      Your job is to extract information from the provided AWS Textract key-value pairs and structure it according to the given JSON schema.

                                      **Inputs:**
                                      1.  **Schema:** A JSON schema that defines the required output structure. This is in the `schema` variable.
                                      2.  **Data:** A list of extracted key-value pairs from an ACORD 125 form. This is in the `text_data` variable.

                                      **Instructions:**
                                      1.  Carefully analyze the key-value pairs in `text_data`.
                                      2.  Map the extracted values to the corresponding fields in the provided `schema`.
                                          * For fields not found in the data, omit them or set their value to `null`.
                                      3.  Your output **must** be a single, valid JSON object that strictly conforms to the provided schema.
                                      4.  Do not include *any* other text, explanations, markdown formatting (like ```json), or commentary in your response. The output must be JSON only.
                                      5.  CRITICAL: Ensure the JSON is valid - no trailing commas, all property names in double quotes, proper escaping.

                                      **Schema:**
                                      {schema_dump}

                                      **text_data**
                                      {text_data}
                                      """
                                }]
                    }
                ]
            }),
        )

        result = json.loads(response["body"].read())
        text = result['content'][0]['text']

        # If data extraction is succesful
        print("✓ Data transformed")

        # Clean up common JSON issues
        text = text.strip()

        # Remove markdown code blocks if present
        if text.startswith('```json'):
            text = text[7:]  # Remove ```json
        if text.startswith('```'):
            text = text[3:]  # Remove ```
        if text.endswith('```'):
            text = text[:-3]  # Remove trailing ```
        text = text.strip()

        # Parse and validate the response
        json_data = json.loads(text)
        validated_data = ACORD125Schema(**json_data)
        print("✓ Schema validated") # If validated

        # Convert to JSON string
        result_json = validated_data.model_dump_json(indent=2)

        return result_json

    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing error at line {e.lineno}, column {e.colno}:")
        print(f"   {e.msg}")
        print("\nProblematic section of response:")
        # Try to show the area around the error
        try:
            lines = text.split('\n')
            start = max(0, e.lineno - 3)
            end = min(len(lines), e.lineno + 2)
            for i in range(start, end):
                marker = " >>> " if i == e.lineno - 1 else "     "
                print(f"{marker}{i+1}: {lines[i]}")
        except:
            print(text[max(0, e.pos-100):e.pos+100])
        return None

    except ValidationError as e:
        print("✗ Validation error - Bedrock output doesn't match schema:")
        print(e.json(indent=2))
        return None

    except Exception as e:
        print("Error invoking model:", e)
        return None

def flatten_json(data, parent_key=''):
    """
    Recursively flattens a nested JSON into key-value pairs.
    Nested keys are joined with dots, lists are indexed.
    """
    items = []

    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            items.extend(flatten_json(v, new_key))
    elif isinstance(data, list):
        for i, v in enumerate(data, start=1):  # start=1 for human-readable index
            new_key = f"{parent_key}[{i}]"
            items.extend(flatten_json(v, new_key))
    else:
        # Primitive value (str, int, float, bool, None)
        items.append((parent_key, data))

    return items

def process_pdf(file):

    if file is None:
        return "No file uploaded.", None

    s3_key, err = upload_to_s3(file)
    if err:
        return f"S3 upload error: {err}", None

    key_map, value_map, block_map = get_kv_map(s3_key)
    kvs = get_kv_relationship(key_map, value_map, block_map)
    extracted_data = get_kv_pairs(kvs)

    # Get JSON schema
    schema = ACORD125Schema.model_json_schema()

    # Run Bedrock
    output_json = run_bedrock_analysis(extracted_data, schema)

    print("Final Output JSON:", output_json) # debugging

    # Create DataFrame from Textract extracted data with confidence scores
    textract_df = pd.DataFrame([
        {
            'Key': item['key'],
            'Value': item['value'],
            'Key Confidence': f"{item['key_confidence']:.2f}%",
            'Value Confidence': f"{item['value_confidence']:.2f}%"
        }
        for item in extracted_data
    ])

    return output_json, textract_df
