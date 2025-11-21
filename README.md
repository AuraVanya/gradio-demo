# AWS Document & Image Analysis with Gradio

A Gradio-based web application that leverages AWS services (Textract, Rekognition, and Bedrock) to extract and structure information from insurance documents and images.

## Features

### 1. ACORD Form Extractor

- Extract information from ACORD 125 Forms (in PDF)
- Display extracted key-value pairs with confidence scores
- Validate data integrity with Pydantic
- Return structured JSON output conforming to ACORD 125 schema

### 2. Motor Quote Analyzer

- **Dual Image Processing:**

  - **Vehicle Image Analysis** (AWS Rekognition):

    - Identify vehicle type, brand, model, and color
    - Extract visible text information (e.g., license plates, decals)
    - Display confidence scores for each analyzed items

  - **Driver's License Extraction** (AWS Textract):
    - Extract driver license information
    - Display confidence scores for each extracted field

- **AI-Powered Data Structuring:**
  - Validate data integrity with Pydantic
  - Return structured JSON with vehicle and driver information

## Tech Stack

- **Gradio:** Provides simple UI and shareable link
- **AWS Services:**
  - **Textract:** Document and form analysis
  - **Rekognition:** Image analysis, text detection, face detection
  - **Bedrock:** Claude Sonnet for intelligent data structuring
  - **S3:** File storage
- **Pydantic schemas:** Validate data structure and integrity

## Architecture

```
┌─────────────────┐
│   Gradio UI     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────────┐
│ ACORD │ │  Motor    │
│Extract│ │  Quote    │
└───┬───┘ └──┬────────┘
    │        │
    │    ┌───┴────┬─────────┐
    │    │        │         │
┌───▼────▼───┐ ┌─▼──────┐ ┌▼────────┐
│  Textract  │ │Rekog   │ │ Bedrock │
│   (Forms)  │ │(Labels)│ │(Claude) │
└────────────┘ └────────┘ └─────────┘
```

## Project Structure

```
gradio-demo/
├── main.py                 # Main Gradio driver
├── functions/
│   ├── acord_extractor.py  # ACORD 125 form processing
│   └── motor_quote.py      # Vehicle & license image analysis
├── schemas/
│   ├── acord_schema.py     # ACORD 125 Pydantic schema
│   └── motor_schema.py     # Motor quote Pydantic schema
├── .env                    # AWS credentials (not in repo)
└── README.md
```

## Prerequisites

- Python 3.12+
- AWS Account with access to:
  - S3
  - Textract
  - Rekognition
  - Bedrock (Claude Sonnet 4.5)
- AWS credentials with appropriate permissions

## Installation

1. Clone the repository:

```bash
git clone https://github.com/AuraVanya/gradio-demo.git
cd gradio-demo
```

2. Create and activate virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install gradio boto3 python-dotenv pandas pydantic
```

4. Create `.env` file with AWS credentials:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-2
```

## Usage

1. Start the application:

```bash
gradio main.py
```

2. Open browser at `http://localhost:7860`

3. **ACORD Extractor Tab:**

   - Upload an ACORD 125 PDF form
   - View extracted data in table format
   - Review structured JSON output

4. **Motor Quote Tab:**
   - Upload a vehicle image (car/motorcycle photo)
   - Upload a driver's license image
   - View extracted data tables for both images
   - Review structured JSON output combining vehicle and driver info

## License

This project is licensed under the terms specified in the LICENSE file.

## Contributing

Contributions are welcome! ૮꒰∩´ ᵕ `∩꒱ა Please feel free to submit a Pull Request.

## Author

AuraVanya
