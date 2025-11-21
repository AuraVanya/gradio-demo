import os
import boto3
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import json

# Load AWS credentials from .env
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-2")
BUCKET_NAME = "textract-colab-temp-bucket"
INFERENCE_PROFILE_ARN = "arn:aws:bedrock:us-east-2:694248134873:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# Initialize clients
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
rekognition_client = boto3.client(
    "rekognition",
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

# --- Image Analyzer --- #

def upload_image_to_s3(file):
    """Uploads image to S3 and returns the S3 path"""

    if file is None:
        return None, "No file provided"

    if not hasattr(file, 'name'):
        return None, "Invalid file object"

    try:
        filename = os.path.basename(file.name)
        s3_key = f"uploads/images/{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        s3_client.upload_file(file.name, BUCKET_NAME, s3_key)
        return s3_key, None # return S3 key and no error
    except Exception as e:
        return None, str(e)

def analyze_image_with_rekognition(s3_key):
    """Analyzes image using AWS Rekognition and returns comprehensive results"""

    results = {}

    try:
        # Detect labels (objects, scenes, activities) - includes image properties like dominant colors
        labels_response = rekognition_client.detect_labels(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_key}},
            MaxLabels=50,
            MinConfidence=70,
            Features=['GENERAL_LABELS', 'IMAGE_PROPERTIES']
        )

        results['labels'] = [
            {
                'name': label['Name'],
                'confidence': round(label['Confidence'], 2),
                'categories': [cat['Name'] for cat in label.get('Categories', [])]
            }
            for label in labels_response['Labels']
        ]

        # Extract dominant colors from foreground only
        if 'ImageProperties' in labels_response:
            image_props = labels_response['ImageProperties']
            if 'Foreground' in image_props and 'DominantColors' in image_props['Foreground']:
                results['dominant_colors'] = [
                    {
                        'color': color.get('SimplifiedColor', color.get('CSSColor', 'Unknown')),
                        'hex': color.get('HexCode', ''),
                        'confidence': round(color.get('PixelPercent', 0), 2)
                    }
                    for color in image_props['Foreground']['DominantColors']
                ]

        # Detect text in image - filter for foreground text based on size and confidence
        text_response = rekognition_client.detect_text(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_key}}
        )

        # Filter for foreground text: higher confidence and larger bounding boxes
        foreground_texts = []
        for text in text_response['TextDetections']:
            geometry = text.get('Geometry', {})
            bbox = geometry.get('BoundingBox', {})

            # Calculate text size (width * height of bounding box)
            text_size = bbox.get('Width', 0) * bbox.get('Height', 0)

            # Filter: confidence > 80% and reasonable size (not tiny background text)
            if text['Confidence'] > 80 and text_size > 0.001:
                foreground_texts.append(text)

        results['text_detections'] = [
            {
                'detected_text': text['DetectedText'],
                'type': text['Type'],
                'confidence': round(text['Confidence'], 2)
            }
            for text in foreground_texts
        ]

        # Detect faces
        faces_response = rekognition_client.detect_faces(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_key}},
            Attributes=['ALL']
        )
        results['faces'] = [
            {
                'confidence': round(face['Confidence'], 2),
                'age_range': face.get('AgeRange', {}),
                'gender': face.get('Gender', {}).get('Value'),
                'emotions': [
                    {'type': emotion['Type'], 'confidence': round(emotion['Confidence'], 2)}
                    for emotion in face.get('Emotions', [])
                ][:3]  # Top 3 emotions
            }
            for face in faces_response['FaceDetails']
        ]

        return results, None

    except Exception as e:
        return None, str(e)

def analyze_license_with_textract(s3_key):
    """Analyzes driver's license using AWS Textract and returns key-value pairs"""

    results = {}

    try:
        # Use Textract to analyze ID document
        response = textract_client.analyze_document(
            Document={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_key}},
            FeatureTypes=['FORMS']
        )

        # Build key-value map
        key_map = {}
        value_map = {}
        block_map = {}

        for block in response['Blocks']:
            block_id = block['Id']
            block_map[block_id] = block

            if block['BlockType'] == "KEY_VALUE_SET":
                if 'KEY' in block.get('EntityTypes', []):
                    key_map[block_id] = block
                elif 'VALUE' in block.get('EntityTypes', []):
                    value_map[block_id] = block

        # Extract key-value pairs
        kv_pairs = []
        for key_id, key_block in key_map.items():
            # Get key text
            key_text = ""
            if 'Relationships' in key_block:
                for relationship in key_block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for child_id in relationship['Ids']:
                            child = block_map.get(child_id)
                            if child and child['BlockType'] == 'WORD':
                                key_text += child['Text'] + " "

            # Get value text
            value_text = ""
            value_confidence = 0
            if 'Relationships' in key_block:
                for relationship in key_block['Relationships']:
                    if relationship['Type'] == 'VALUE':
                        for value_id in relationship['Ids']:
                            value_block = value_map.get(value_id)
                            if value_block:
                                value_confidence = value_block.get('Confidence', 0)
                                if 'Relationships' in value_block:
                                    for val_rel in value_block['Relationships']:
                                        if val_rel['Type'] == 'CHILD':
                                            for child_id in val_rel['Ids']:
                                                child = block_map.get(child_id)
                                                if child and child['BlockType'] == 'WORD':
                                                    value_text += child['Text'] + " "

            kv_pairs.append({
                'key': key_text.strip(),
                'value': value_text.strip(),
                'key_confidence': key_block.get('Confidence', 0),
                'value_confidence': value_confidence
            })

        results['key_value_pairs'] = kv_pairs
        return results, None

    except Exception as e:
        return None, str(e)

def run_bedrock_analysis(vehicle_data, license_data, schema):
    """Use Bedrock to transform extracted data into structured JSON format"""

    combined_data = {
        "vehicle_analysis": vehicle_data,
        "license_data": license_data
    }

    data_dump = json.dumps(combined_data, indent=2)
    schema_dump = json.dumps(schema, indent=2)

    print("Transforming data with Bedrock...")

    try:
        response = bedrock_runtime_client.invoke_model(
            modelId=INFERENCE_PROFILE_ARN,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": [{
                            "type": "text",
                            "text": f"""
                                    You are an expert in vehicle insurance data extraction and driver's license interpretation.

                                    **Task:**
                                    Extract and structure vehicle and driver information from the provided AWS Rekognition and Textract data according to the given JSON schema.

                                    **Inputs:**
                                    1. **Schema:** A JSON schema defining the required output structure.
                                    2. **Data:** Combined data from:
                                    - vehicle_analysis: Rekognition results (colors, labels, text detections)
                                    - license_data: Textract key-value pairs from driver's license

                                    **Instructions:**
                                    1. Carefully analyze both data sources.
                                    2. For vehicle information:
                                    - Extract type, brand, model, year from labels (e.g., "Car", "Toyota", "Sedan", etc.)
                                    - Use dominant colors for the color field
                                    - Extract license plate, chassis number, engine number from text detections
                                    - Use reasonable inference for transmission type if visible in labels
                                    3. For driver information:
                                    - Map Textract key-value pairs to driver fields
                                    - Common license fields: license number, name, surname, DOB, address, valid from/to dates
                                    - Format dates as YYYY-MM-DD if possible
                                    4. For fields not found in data, set value to null or empty string as appropriate.
                                    5. Output **must** be a single, valid JSON object conforming to the schema.
                                    6. Do not include any markdown formatting, explanations, or commentary.
                                    7. Ensure valid JSON: no trailing commas, double quotes for properties, proper escaping.

                                    **Schema:**
                                    {schema_dump}

                                    **Data:**
                                    {data_dump}
                                    """
                        }]
                    }
                ]
            }),
        )

        result = json.loads(response["body"].read())
        text = result['content'][0]['text']

        print("✓ Data transformed")

        # Clean up markdown formatting
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()

        # Parse JSON
        json_data = json.loads(text)
        print("✓ JSON parsed successfully")

        return json.dumps(json_data, indent=2)

    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"✗ Bedrock error: {e}")
        return None

schema = {
            "vehicle": {
                "type": "string",
                "brand": "string",
                "model": "string",
                "year": "integer",
                "transmission": "string",
                "licensePlate": "string",
                "chassisNumber": "string",
                "engineNumber": "string",
                "color": "string"
            },
            "driver": {
                "driverLicenseId": "string",
                "name": "string",
                "surname": "string",
                "dateOfBirth": "string (YYYY-MM-DD)",
                "countryOfBirth": "string",
                "validFrom": "string (YYYY-MM-DD)",
                "validTo": "string (YYYY-MM-DD)",
                "issuingAuthority": "string",
                "address": "string",
                "addressMatchesDVLA": "boolean"
            }
        }

def process_images(vehicle_image, license_image):
    """Main function to process both uploaded images"""


    # Process vehicle image with Rekognition
    if vehicle_image is not None:
        s3_key, err = upload_image_to_s3(vehicle_image)
        if err:
            vehicle_df = pd.DataFrame([{'Error': f"S3 upload error: {err}"}])
        else:
            print(f"Vehicle image uploaded to S3: {s3_key}")
            vehicle_results, err = analyze_image_with_rekognition(s3_key)
            if err:
                vehicle_df = pd.DataFrame([{'Error': f"Rekognition analysis error: {err}"}])
            else:
                # Create DataFrame for vehicle analysis
                table_data = []

                # Add dominant colors first
                for color in vehicle_results.get('dominant_colors', []):
                    table_data.append({
                        'Category': 'Color',
                        'Key': color['color'],
                        'Value': color['hex'],
                        'Confidence': f"{color['confidence']:.2f}%"
                    })

                # Add labels
                for label in vehicle_results.get('labels', []):
                    table_data.append({
                        'Category': 'Label',
                        'Key': label['name'],
                        'Value': ', '.join(label['categories']) if label['categories'] else '',
                        'Confidence': f"{label['confidence']:.2f}%"
                    })

                # Add text detections
                for text in vehicle_results.get('text_detections', []):
                    if text['type'] == 'LINE':
                        table_data.append({
                            'Category': 'Text',
                            'Key': text['detected_text'],
                            'Value': text['type'],
                            'Confidence': f"{text['confidence']:.2f}%"
                        })

                # Add face detections
                for i, face in enumerate(vehicle_results.get('faces', []), 1):
                    emotions = ', '.join([f"{e['type']}" for e in face['emotions'][:3]])
                    table_data.append({
                        'Category': 'Face',
                        'Key': f"Person {i}",
                        'Value': f"Age: {face['age_range'].get('Low', 'N/A')}-{face['age_range'].get('High', 'N/A')}, Gender: {face.get('gender', 'N/A')}, Emotions: {emotions}",
                        'Confidence': f"{face['confidence']:.2f}%"
                    })

                vehicle_df = pd.DataFrame(table_data) if table_data else pd.DataFrame([{'Message': 'No data extracted'}])
    else:
        vehicle_df = pd.DataFrame([{'Message': 'No vehicle image uploaded'}])

    # Process license image with Textract
    if license_image is not None:
        s3_key, err = upload_image_to_s3(license_image)
        if err:
            license_df = pd.DataFrame([{'Error': f"S3 upload error: {err}"}])
        else:
            print(f"License image uploaded to S3: {s3_key}")
            license_results, err = analyze_license_with_textract(s3_key)
            if err:
                license_df = pd.DataFrame([{'Error': f"Textract analysis error: {err}"}])
            else:
                # Create DataFrame for license analysis
                table_data = []
                for item in license_results.get('key_value_pairs', []):
                    if item['key']:  # Only include entries with keys
                        table_data.append({
                            'Key': item['key'],
                            'Value': item['value'],
                            'Key Confidence': f"{item['key_confidence']:.2f}%",
                            'Value Confidence': f"{item['value_confidence']:.2f}%"
                        })

                license_df = pd.DataFrame(table_data) if table_data else pd.DataFrame([{'Message': 'No data extracted'}])
    else:
        license_df = pd.DataFrame([{'Message': 'No license image uploaded'}])

    # Generate structured JSON with Bedrock if both images processed successfully
    structured_json = "No structured output generated. One or both images were missing."

    if vehicle_results and license_results:
        result = run_bedrock_analysis(vehicle_results, license_results, schema)
        if result:
            structured_json = result

    return structured_json, vehicle_df, license_df
