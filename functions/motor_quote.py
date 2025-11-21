import os
import boto3
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

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

# --- Image Analyzer --- #

def upload_image_to_s3(file):
    """Uploads image to S3 and returns the S3 path"""
    import tempfile
    import shutil

    # Get the original filename
    if hasattr(file, 'name'):
        original_name = os.path.basename(file.name)
    else:
        original_name = "uploaded_image.jpg"

    s3_key = f"uploads/images/{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"

    try:
        # Handle different file input types from Gradio
        if isinstance(file, str):
            # file is a path string
            file_path = file
        elif hasattr(file, 'name'):
            # file is a file-like object with a name attribute
            file_path = file.name
        else:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(original_name)[1]) as tmp_file:
                shutil.copyfileobj(file, tmp_file)
                file_path = tmp_file.name

        # Upload to S3
        with open(file_path, 'rb') as f:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=f,
                ContentType='image/jpeg'
            )

        return s3_key, None  # return S3 key and no error
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

def process_images(vehicle_image, license_image):
    """Main function to process both uploaded images"""

    vehicle_df = None
    license_df = None

    # Process vehicle image with Rekognition
    if vehicle_image is not None:
        s3_key, err = upload_image_to_s3(vehicle_image)
        if err:
            vehicle_df = pd.DataFrame([{'Error': f"S3 upload error: {err}"}])
        else:
            print(f"Vehicle image uploaded to S3: {s3_key}")
            results, err = analyze_image_with_rekognition(s3_key)
            if err:
                vehicle_df = pd.DataFrame([{'Error': f"Rekognition analysis error: {err}"}])
            else:
                # Create DataFrame for vehicle analysis
                table_data = []

                # Add dominant colors first
                for color in results.get('dominant_colors', []):
                    table_data.append({
                        'Category': 'Color',
                        'Key': color['color'],
                        'Value': color['hex'],
                        'Confidence': f"{color['confidence']:.2f}%"
                    })

                # Add labels
                for label in results.get('labels', []):
                    table_data.append({
                        'Category': 'Label',
                        'Key': label['name'],
                        'Value': ', '.join(label['categories']) if label['categories'] else '',
                        'Confidence': f"{label['confidence']:.2f}%"
                    })

                # Add text detections
                for text in results.get('text_detections', []):
                    if text['type'] == 'LINE':
                        table_data.append({
                            'Category': 'Text',
                            'Key': text['detected_text'],
                            'Value': text['type'],
                            'Confidence': f"{text['confidence']:.2f}%"
                        })

                # Add face detections
                for i, face in enumerate(results.get('faces', []), 1):
                    emotions = ', '.join([f"{e['type']}" for e in face['emotions'][:3]])
                    table_data.append({
                        'Category': 'Face',
                        'Key': f"Person {i}",
                        'Value': f"Age: {face['age_range'].get('Low', 'N/A')}-{face['age_range'].get('High', 'N/A')}, Gender: {face.get('gender', 'N/A')}, Emotions: {emotions}",
                        'Confidence': f"{face['confidence']:.2f}%"
                    })

                vehicle_df = pd.DataFrame(table_data)
    else:
        vehicle_df = pd.DataFrame([{'Message': 'No vehicle image uploaded'}])

    # Process license image with Textract
    if license_image is not None:
        s3_key, err = upload_image_to_s3(license_image)
        if err:
            license_df = pd.DataFrame([{'Error': f"S3 upload error: {err}"}])
        else:
            print(f"License image uploaded to S3: {s3_key}")
            results, err = analyze_license_with_textract(s3_key)
            if err:
                license_df = pd.DataFrame([{'Error': f"Textract analysis error: {err}"}])
            else:
                # Create DataFrame for license analysis
                table_data = []
                for item in results.get('key_value_pairs', []):
                    if item['key']:  # Only include entries with keys
                        table_data.append({
                            'Key': item['key'],
                            'Value': item['value'],
                            'Key Confidence': f"{item['key_confidence']:.2f}%",
                            'Value Confidence': f"{item['value_confidence']:.2f}%"
                        })

                license_df = pd.DataFrame(table_data)
    else:
        license_df = pd.DataFrame([{'Message': 'No license image uploaded'}])

    return vehicle_df, license_df
