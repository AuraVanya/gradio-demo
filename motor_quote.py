import os
import boto3
from dotenv import load_dotenv
import gradio as gr
import json
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
        # Detect labels (objects, scenes, activities)
        labels_response = rekognition_client.detect_labels(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_key}},
            MaxLabels=50,
            MinConfidence=70
        )

        results['labels'] = [
            {
                'name': label['Name'],
                'confidence': round(label['Confidence'], 2),
                'categories': [cat['Name'] for cat in label.get('Categories', [])]
            }
            for label in labels_response['Labels']
        ]

        # Detect text in image
        text_response = rekognition_client.detect_text(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_key}}
        )
        results['text_detections'] = [
            {
                'detected_text': text['DetectedText'],
                'type': text['Type'],
                'confidence': round(text['Confidence'], 2)
            }
            for text in text_response['TextDetections']
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

def process_image(file):
    """Main function to process uploaded image"""

    if file is None:
        return "No file uploaded.", None

    # Upload to S3
    s3_key, err = upload_image_to_s3(file)
    if err:
        return f"S3 upload error: {err}", None

    print(f"Image uploaded to S3: {s3_key}")

    # Analyze with Rekognition
    results, err = analyze_image_with_rekognition(s3_key)
    if err:
        return f"Rekognition analysis error: {err}", None

    # Format as JSON
    output_json = json.dumps(results, indent=2)

    # Flatten for tabular display
    table_data = []

    # Add labels
    for label in results.get('labels', []):
        table_data.append({
            'Category': 'Label',
            'Name': label['name'],
            'Confidence': f"{label['confidence']}%",
            'Details': ', '.join(label['categories']) if label['categories'] else ''
        })

    # Add text detections
    for text in results.get('text_detections', []):
        if text['type'] == 'LINE':  # Only show lines, not individual words
            table_data.append({
                'Category': 'Text',
                'Name': text['detected_text'],
                'Confidence': f"{text['confidence']}%",
                'Details': text['type']
            })

    # Add face detections
    for i, face in enumerate(results.get('faces', []), 1):
        emotions = ', '.join([f"{e['type']} ({e['confidence']}%)" for e in face['emotions']])
        table_data.append({
            'Category': 'Face',
            'Name': f"Person {i}",
            'Confidence': f"{face['confidence']}%",
            'Details': f"Age: {face['age_range'].get('Low', 'N/A')}-{face['age_range'].get('High', 'N/A')}, Gender: {face.get('gender', 'N/A')}, Emotions: {emotions}"
        })

    df = pd.DataFrame(table_data)

    return output_json, df
