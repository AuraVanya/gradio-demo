"""
FNOL Triage Module - Complete Rewrite for P0 Requirements
Implements all critical requirements from the specification
"""

import json
import os
import re
import time
from datetime import datetime
from typing import Dict
import boto3
import zipfile
import xml.etree.ElementTree as ET
from functions.acord_extractor import (
    upload_to_s3 as acord_upload_to_s3,
    get_kv_map,
    get_kv_relationship,
    get_kv_pairs,
)
from functions.visual_analysis import (
    upload_image_to_s3,
    analyze_image_with_rekognition,
)
from dotenv import load_dotenv

load_dotenv()

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-2")
BUCKET_NAME = os.getenv("BUCKET_NAME", "textract-colab-temp-bucket")
INFERENCE_PROFILE_ARN = os.getenv(
    "FNOL_BEDROCK_INFERENCE_PROFILE_ARN",
    os.getenv(
        "INFERENCE_PROFILE_ARN",
        "arn:aws:bedrock:us-east-2:694248134873:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    ),
)

bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
textract_client = boto3.client(
    "textract",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# Load data files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

with open(os.path.join(DATA_DIR, "nacora_handler_pool.json"), "r") as f:
    HANDLER_POOL = json.load(f)["handlers"]

with open(os.path.join(DATA_DIR, "nacora_product_taxonomy.json"), "r") as f:
    PRODUCT_TAXONOMY = json.load(f)["categories"]

with open(os.path.join(DATA_DIR, "country_region_mapping.json"), "r") as f:
    REGION_DATA = json.load(f)
    COUNTRY_TO_REGION = REGION_DATA["country_to_region"]

# Global counter for FNOL IDs
_fnol_counter = 0


def _generate_fnol_id() -> str:
    """Generate FNOL ID in format FNOL-YYMMDD-NNNN"""
    global _fnol_counter
    _fnol_counter += 1
    now = datetime.now()
    return f"FNOL-{now.strftime('%y%m%d')}-{_fnol_counter:04d}"


def _normalize_text(*parts) -> str:
    """Combine and normalize text parts"""
    text = "\n".join(p for p in parts if p)
    return re.sub(r"\s+", " ", text).strip()


def _upload_to_s3(file_path):
    filename = os.path.basename(file_path)
    s3_key = f"fnol-uploads/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    s3_client.upload_file(file_path, BUCKET_NAME, s3_key)
    return s3_key


def _delete_s3_object(s3_key):
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
    except Exception:
        pass


def _extract_docx_text(file_path):
    texts = []
    with zipfile.ZipFile(file_path) as docx_zip:
        with docx_zip.open("word/document.xml") as doc_xml:
            tree = ET.parse(doc_xml)
            root = tree.getroot()
            for elem in root.iter():
                if elem.tag.endswith("}t") and elem.text:
                    texts.append(elem.text)
    return " ".join(texts)


def _extract_text_from_upload(file_obj):
    """Extract text from uploaded document"""
    if file_obj is None or not hasattr(file_obj, "name"):
        return ""
    file_path = file_obj.name
    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".txt", ".md", ".json"]:
        try:
            with open(file_path, "rb") as handle:
                return handle.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""

    if ext in [".pdf", ".tif", ".tiff"]:
        s3_key = None
        try:
            s3_key, err = acord_upload_to_s3(file_obj)
            if err:
                return f"S3 upload error: {err}"
            key_map, value_map, block_map = get_kv_map(s3_key)
            kvs = get_kv_relationship(key_map, value_map, block_map)
            extracted_data = get_kv_pairs(kvs)
            lines = [f"{item['key']}: {item['value']}" for item in extracted_data if item.get("key")]
            return "\n".join(lines)
        finally:
            if s3_key:
                _delete_s3_object(s3_key)

    if ext in [".png", ".jpg", ".jpeg"]:
        s3_key = None
        try:
            s3_key, err = upload_image_to_s3(file_obj)
            if err:
                return f"S3 upload error: {err}"
            results, err = analyze_image_with_rekognition(s3_key)
            if err:
                return f"Rekognition analysis error: {err}"
            labels = [f"Label: {item['name']} ({item['confidence']:.2f}%)" for item in results.get("labels", [])]
            texts = [f"Text: {item['detected_text']} ({item['confidence']:.2f}%)" for item in results.get("text_detections", [])]
            colors = [f"Color: {item['color']} {item['hex']}" for item in results.get("dominant_colors", [])]
            return "\n".join(labels + texts + colors)
        finally:
            if s3_key:
                _delete_s3_object(s3_key)

    if ext == ".docx":
        return _extract_docx_text(file_path)

    if ext == ".doc":
        return "DOC file provided. Please upload DOCX or PDF for text extraction."

    return ""


def _build_system_prompt() -> str:
    """Build comprehensive system prompt with business-aligned output format"""

    # Format handler pool
    handler_list = []
    for h in HANDLER_POOL:
        handler_list.append(
            f"  {h['id']}: {h['name']} ({h['seniority']}) - Region: {h['region']}, "
            f"Specialities: {', '.join(h['specialities'])}, Languages: {', '.join(h['languages'])}, "
            f"Max Severity: {h['max_severity']}, Email: {h['email']}, Phone: {h['phone']}"
        )

    # Format product taxonomy
    taxonomy_list = []
    for category in PRODUCT_TAXONOMY:
        first_grouping = category["first_grouping"]
        first_code = category["first_grouping_code"]
        taxonomy_list.append(f"\n{first_grouping} ({first_code}):")
        for product in category["products"]:
            taxonomy_list.append(f"  - {product['product_code']}: {product['product_name']}")

    # Format country-to-region mapping
    region_examples = []
    for region in ["DACH", "Benelux", "UK_Nordics", "Iberia", "MENA_Turkey", "LATAM", "Africa", "APAC"]:
        countries = [code for code, r in COUNTRY_TO_REGION.items() if r == region]
        if countries:
            region_examples.append(f"  {region}: {', '.join(countries[:5])}")

    prompt = f"""You are an expert FNOL (First Notice of Loss) triage system for Nacora, a global insurance broker.
Your output MUST be business-friendly, actionable, and transparent for insurance professionals.

YOUR TASK:
Analyze the incoming loss notification and produce a structured triage decision that handlers can act on immediately.

CRITICAL REQUIREMENTS:
1. ✅ Use ONLY approved insurance product taxonomy (NO free-text categories)
2. ✅ Explain severity with 2-4 clear drivers showing impact level (High/Medium/Low)
3. ✅ Identify key signals (document_type, financial_indicator, incident_severity, etc.)
4. ✅ Provide actionable next steps (system-level AND handler-level)
5. ✅ Use ONLY real Nacora handlers from the pool below
6. ✅ Flag ALL missing data in data_gaps with importance ratings (Critical/High/Medium/Low)
7. ✅ Show transparent decision logic (summary + 1-3 key factors)

=== NACORA HANDLER POOL (34 handlers) ===
{chr(10).join(handler_list)}

=== APPROVED INSURANCE PRODUCT TAXONOMY ===
Use ONLY these categories. NEVER generate custom/free-text types.
{chr(10).join(taxonomy_list)}

Classification Display Format: "First Grouping – Product Name"
Example: "Property – Construction all risk" or "Marine Cargo – Marine Cargo via GFH"

=== COUNTRY TO REGION MAPPING ===
{chr(10).join(region_examples)}

=== HANDLER ROUTING RULES (apply in priority order) ===
Priority 1 (HIGHEST): severity == Critical AND claim_value > 500,000 → H-GL-002 (David Okonkwo)
Priority 2: lob IN [trade_credit, professional_indemnity] → H-GL-003 (Nina Bergström)
Priority 3: survey/inspection needed → ADD H-GL-004 (Youssef Benali) as SECONDARY
Priority 4 (DEFAULT - REGION MANDATORY):
  STEP 1: Detect claim country → map to region using country_region_mapping
  STEP 2: FILTER handlers to ONLY those matching claim region
  STEP 3: Among same-region handlers, rank by: speciality match > language match > seniority

CRITICAL: Handler MUST be from same region as claim. Never assign cross-region unless no handlers exist in claim region.
Example: Netherlands claim → ONLY Benelux handlers (H-BNL-001 to H-BNL-004)
Example: Germany claim → ONLY DACH handlers (H-DACH-001 to H-DACH-006)
Example: Turkey claim → ONLY MENA_Turkey handlers (H-MT-001, H-MT-002)

EXCEPTIONS (Cross-region allowed ONLY for):
- Priority 1: H-GL-002 (Global, handles any region for critical/high-value claims)
- Priority 2: H-GL-003 (Global, handles any region for Trade Credit/PI)
- Priority 3 secondary: H-GL-004 (Global, survey/inspection specialist)
All other handlers: STRICT same-region matching REQUIRED.

=== TRADE CREDIT / PROFESSIONAL INDEMNITY DETECTION (REQ-13) ===
Route to H-GL-003 (Nina Bergström) when claim mentions ANY of these keywords:
- Trade Credit: insolvency, insolvent, bankruptcy, bankrupt, credit default, non-payment,
  debtor failure, receivables, credit insurance, buyer insolvency, payment default
- Professional Indemnity: professional negligence, errors and omissions, E&O, broker error,
  misrepresentation, professional liability, advice negligence, duty of care breach,
  malpractice, professional misconduct, fiduciary breach

Nina Bergström (H-GL-003) is the ONLY specialist for financial lines globally.
Do NOT route financial lines to regional handlers - ALWAYS use H-GL-003 as primary.

=== SECONDARY HANDLER RULES ===
- Survey/inspection needed → ALWAYS add H-GL-004 as secondary
- Critical + value >500k → add H-GL-002 as secondary (or primary if Priority 1)
- Trade credit or PI → H-GL-003 is ALWAYS primary
- Multilingual matching: CRITICAL - match detected input language to handler languages

=== MULTILINGUAL HANDLER MATCHING (REQ-12) ===
IMPORTANT: Language matching happens WITHIN the claim's region ONLY.
Do NOT match language if it means assigning a handler from a different region.

When input language is detected, prefer handlers who speak that language IN THE SAME REGION:
- Turkish input (TR detected) + Turkey claim → H-MT-001 (Emre Yilmaz), H-MT-002 (Fatima Al-Hassan)
- German input (DE detected) + DACH claim → H-DACH-001 through H-DACH-006
- Dutch input (NL detected) + Benelux claim → H-BNL-001 through H-BNL-004
- Spanish input (ES detected) + Iberia claim → H-ES-001 (Antonio Yut)
- Spanish input (ES detected) + LATAM claim → H-LATAM-001 (Pablo Fuentes)
- Portuguese input (PT detected) + LATAM claim → H-LATAM-002 (Valentina Cruz), H-LATAM-003 (Rodrigo Mendes)
- French input (FR detected) + Benelux claim → H-BNL-001 (Celine Dubois)
- Arabic input (AR detected) + MENA claim → H-MT-002 (Fatima Al-Hassan), H-GL-004 (Youssef Benali)
- Chinese input (ZH detected) + APAC claim → H-APAC-001 (Mei-Lin Chow)
- Japanese input (JA detected) + APAC claim → H-APAC-002 (Hiroshi Nakamura)
- Swedish/Nordic input (SV/NO/DA detected) + UK_Nordics claim → H-UKN-002 (Astrid Lindqvist), H-UKN-004 (Erik Halvorsen)

Region match is MANDATORY. Language match is a tiebreaker WITHIN the region.
If no same-region handler speaks the detected language, use any same-region handler (English fallback).

=== SEVERITY SCORING (0-100) ===
Score based on:
- Value: >5M = +40, 1-5M = +30, 250k-1M = +20, <250k = +10
- Injury/fatality = +25 (mark as PRIMARY factor)
- Fire/explosion = +15 (PRIMARY)
- Total loss = +15 (PRIMARY)
- Temperature breach/spoilage = +15 (SECONDARY)
- Multiple parties affected = +10 (SECONDARY)
- Legal/regulatory exposure = +15 (SECONDARY)
- Urgent request = +10 (MINOR)
- Business interruption = +15 (SECONDARY)

Levels: Critical (70-100), High (50-69), Medium (30-49), Low (0-29)

=== DATA GAPS DETECTION ===
Check for these fields and flag as not_detected if missing:
- geography (country, city, location)
- policy.number
- financial (amount, currency)
- insurance_product
- third party involvement
- date of loss

=== OUTPUT FORMAT (STRICT JSON - BUSINESS-ALIGNED) ===
Return ONLY valid JSON matching this EXACT structure. NO markdown. NO chain-of-thought.

{{
  "fnol_id": "FNOL-260410-0001",
  "timestamp": "2026-04-10T14:30:00Z",
  "detected_language": {{
    "code": "EN",
    "name": "English",
    "confidence": 95
  }},
  "claim_type": {{
    "first_grouping": "Marine Cargo",
   "first_grouping_code": "MCARGO",
    "product_name": "Marine Cargo via GFH",
    "product_code": "MCARGO-002",
    "display_format": "Marine Cargo – Marine Cargo via GFH"
  }},
  "severity": {{
    "level": "High",
    "score": 65,
    "drivers": [
      {{"driver": "High-value shipment (€240,000)", "impact": "High"}},
      {{"driver": "Total loss claimed by insured", "impact": "High"}},
      {{"driver": "Time-sensitive settlement required", "impact": "Medium"}}
    ]
  }},
  "key_signals_identified": [
    {{"signal_type": "financial_indicator", "description": "Loss value €240,000 detected"}},
    {{"signal_type": "document_type", "description": "Bill of Lading reference found"}},
    {{"signal_type": "incident_severity", "description": "Total loss keywords present"}},
    {{"signal_type": "geographic_marker", "description": "Rotterdam port mentioned"}}
  ],
  "decision_logic": {{
    "summary": "High-value marine cargo claim requiring specialized handler with cargo expertise",
    "key_factors": [
      "Value exceeds €200K threshold for high priority",
      "Marine cargo product confirmed from B/L reference",
      "Geographic match: Netherlands → Benelux region"
    ]
  }},
  "system_next_action": {{
    "action": "Assign to specialized cargo handler for immediate processing",
    "rationale": "High value and total loss claim requires experienced handler within 24h SLA"
  }},
  "handler_next_action": {{
    "action": "Request Bill of Lading, CMR note, and damage survey within 24 hours",
    "priority": "Urgent"
  }},
  "confidence": {{
    "score": 88,
    "explanation": "High confidence due to clear product type, complete financial data, and specific location",
    "factors_affecting": [
      "Complete documentation references provided",
      "Clear geographic and product indicators",
      "Structured input format"
    ]
  }},
  "handlers": {{
    "primary": {{
      "handler_id": "H-BNL-002",
      "name": "Lars van der Berg",
      "match_reason": "REGION MATCH: Benelux (NL claim) → Benelux handler | Marine cargo specialist | Dutch language match",
      "contact_email": "l.vandenberg@nacora.com",
      "contact_phone": "+31 10 1234 5612"
    }},
    "secondary": null
  }},
  "data_gaps": [
    {{"field": "policy_number", "prompt": "Please provide the policy number or certificate reference", "importance": "Critical"}},
    {{"field": "date_of_loss", "prompt": "Please confirm the exact date when the loss occurred", "importance": "High"}},
    {{"field": "third_party_liability", "prompt": "Is there any third-party liability involved?", "importance": "Medium"}}
  ],
  "financial": {{
    "amount": 240000,
    "currency": "EUR",
    "original_text": "€240,000"
  }},
  "geography": {{
    "country": "NL",
    "country_name": "Netherlands",
    "city": "Rotterdam",
    "region": "Benelux"
  }},
  "policy": {{
    "number": null,
    "type": "Marine Cargo Open Cover"
  }},
  "bms_integration": {{
    "policy_number_field": "Links to existing policy/certificate in NacoraHub",
    "handler_id_field": "Pre-fills Assigned To: H-BNL-002 (Lars van der Berg)",
    "product_code_field": "Maps to BMS product code MCARGO-002",
    "severity_field": "Sets SLA: High = 24h response required"
  }}
}}

=== SIGNAL TYPES (For key_signals_identified) ===
- "document_type": Document references (B/L, CMR, invoice, medical report, certificate)
- "financial_indicator": Amount, currency, value mentions, financial thresholds
- "incident_severity": Total loss, partial damage, fire, explosion, injury, fatality
- "data_quality": Complete vs incomplete, structured vs unstructured input
- "policy_type": Open cover, single risk, global program, local policy
- "geographic_marker": Country, city, port, warehouse, specific location
- "other": Any other relevant signal

=== NEXT ACTION PRIORITY LEVELS ===
- "Immediate": Requires action within 4 hours (Critical severity, life-threatening)
- "Urgent": Requires action within 24 hours (High severity, time-sensitive)
- "Standard": Normal processing timeline (Medium severity)
- "Low": Can be queued (Low severity, administrative)

=== EDGE CASES ===
- Thin input: Low confidence scores, extensive data_gaps, importance ratings
- No currency: Set financial.amount as null
- Unknown country: Use region "Global", flag geography data gaps
- Trade Credit/PI keywords: ALWAYS route to H-GL-003
- Survey keywords: Add H-GL-004 as secondary handler"""

    return prompt


def _invoke_bedrock(fnol_text: str) -> Dict:
    """Invoke Bedrock with the FNOL text and return parsed JSON"""

    system_prompt = _build_system_prompt()
    user_prompt = f"""FNOL INPUT:
{fnol_text}

Return the complete JSON triage output as specified. Remember:
- Use ONLY approved product taxonomy (no free-text categories)
- Use ONLY real handlers from the handler pool
- Provide 2-4 severity drivers with clear impact levels
- Include key_signals_identified and decision_logic
- Provide both system_next_action AND handler_next_action
- Flag all missing data in data_gaps with importance ratings
- Include confidence score with explanation
- NO markdown code fences - just pure JSON"""

    try:
        response = bedrock_runtime_client.invoke_model(
            modelId=INFERENCE_PROFILE_ARN,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.1,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": user_prompt}],
                    }
                ],
            }),
        )
    except Exception as exc:
        raise RuntimeError(f"Bedrock invoke_model failed: {exc}") from exc

    # Parse response
    body = response.get("body")
    payload = body.read().decode("utf-8") if hasattr(body, "read") else body

    if not payload or not str(payload).strip():
        raise ValueError("Empty Bedrock response body")

    try:
        result = json.loads(payload)
        if isinstance(result, dict):
            content = result.get("content")
            if isinstance(content, list) and content:
                text = content[0].get("text", "").strip()
            else:
                raise ValueError(f"Unexpected response format: {str(result)[:200]}")
    except json.JSONDecodeError:
        raise ValueError(f"Non-JSON response: {str(payload)[:200]}")

    # Clean up markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        if text.endswith ("```"):
            text = text[:-3].strip()

    # Parse as JSON
    try:
        triage_data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {exc}. Raw: {text[:300]}") from exc

    return triage_data


def _enrich_with_handler_details(triage_data: Dict) -> Dict:
    """Enrich handler recommendations with full contact details"""

    handlers = triage_data.get("handlers", {})

    # Enrich primary handler
    if "primary" in handlers:
        handler_id = handlers["primary"]["handler_id"]
        handler_data = next((h for h in HANDLER_POOL if h["id"] == handler_id), None)
        if handler_data:
            handlers["primary"]["name"] = handler_data["name"]
            handlers["primary"]["email"] = handler_data["email"]
            handlers["primary"]["phone"] = handler_data["phone"]
            handlers["primary"]["role"] = f"{handler_data['seniority']} {handler_data['region']} Handler"
            handlers["primary"]["specialities"] = handler_data["specialities"]

    # Enrich secondary handler
    if "secondary" in handlers and handlers["secondary"]:
        handler_id = handlers["secondary"]["handler_id"]
        handler_data = next((h for h in HANDLER_POOL if h["id"] == handler_id), None)
        if handler_data:
            handlers["secondary"]["name"] = handler_data["name"]
            handlers["secondary"]["email"] = handler_data["email"]
            handlers["secondary"]["phone"] = handler_data["phone"]
            handlers["secondary"]["role"] = handlers["secondary"].get("role_in_claim", f"{handler_data['seniority']} Specialist")

    triage_data["handlers"] = handlers
    return triage_data


def triage_fnol(
    free_text: str,
    doc_file,
    insured_name: str,
    policy_number: str,
    location: str,
    estimated_value: str,
    urgency_notes: str,
    documents_list: str,
    extra_notes: str,
) -> str:
    """
    Main FNOL triage function
    Returns JSON string with complete triage output
    """

    # Extract document text if uploaded
    doc_text = _extract_text_from_upload(doc_file)

    # Combine all inputs
    structured_text = _normalize_text(
        free_text,
        doc_text,
        f"Insured: {insured_name}" if insured_name else "",
        f"Policy: {policy_number}" if policy_number else "",
        f"Location: {location}" if location else "",
        f"Estimated value: {estimated_value}" if estimated_value else "",
        f"Urgency: {urgency_notes}" if urgency_notes else "",
        f"Documents: {documents_list}" if documents_list else "",
        f"Notes: {extra_notes}" if extra_notes else "",
    )

    # Handle empty input
    if not structured_text or len(structured_text) < 10:
        fallback = {
            "fnol_id": _generate_fnol_id(),
            "timestamp": datetime.now().isoformat() + "Z",
            "detected_language": {"code": "EN", "name": "English", "confidence": 50},
            "claim_type": {
                "first_grouping": "Unclassified",
                "first_grouping_code": "UNC",
                "product_name": "Insufficient Information",
                "product_code": "UNC-000",
                "display_format": "Unclassified – Insufficient Information"
            },
            "severity": {
                "level": "Low",
                "score": 0,
                "drivers": [
                    {"driver": "No claim details provided", "impact": "Low"}
                ]
            },
            "key_signals_identified": [
                {"signal_type": "data_quality", "description": "Input below minimum length threshold"}
            ],
            "decision_logic": {
                "summary": "Cannot triage without claim information",
                "key_factors": [
                    "Input length insufficient for analysis",
                    "No claim description provided"
                ]
            },
            "system_next_action": {
                "action": "Request complete FNOL submission with all required fields",
                "rationale": "Insufficient data to perform automated triage"
            },
            "handler_next_action": {
                "action": "Contact submitter to request full claim details",
                "priority": "Standard"
            },
            "confidence": {
                "score": 0,
                "explanation": "No confidence due to missing claim information",
                "factors_affecting": [
                    "Input below minimum threshold",
                    "No extractable claim data"
                ]
            },
            "handlers": {
                "primary": {
                    "handler_id": "H-GL-002",
                    "name": "David Okonkwo",
                    "match_reason": "Global escalation for incomplete submission",
                    "contact_email": "d.okonkwo@nacora.com",
                    "contact_phone": "+44 20 1234 5632"
                },
                "secondary": null
            },
            "data_gaps": [
                {"field": "claim_description", "prompt": "Please provide a description of what happened", "importance": "Critical"},
                {"field": "policy_number", "prompt": "Please provide the policy number", "importance": "Critical"},
                {"field": "date_of_loss", "prompt": "Please provide the date of loss", "importance": "Critical"},
                {"field": "location", "prompt": "Please provide where the loss occurred", "importance": "High"},
                {"field": "estimated_value", "prompt": "Please provide the estimated value of the loss", "importance": "High"}
            ],
            "financial": {"amount": None, "currency": None, "original_text": None},
            "geography": {
                "country": None,
                "country_name": None,
                "city": None,
                "region": "Global"
            },
            "policy": {"number": None, "type": None},
            "bms_integration": {
                "policy_number_field": "Links to existing policy record in NacoraHub",
                "handler_id_field": "Pre-fills Assigned To: H-GL-002 (David Okonkwo)",
                "product_code_field": "Maps to BMS product code UNC-000",
                "severity_field": "Sets SLA: Low = 5 days response"
            }
        }
        return json.dumps(fallback, ensure_ascii=False, indent=2)

    try:
        # Invoke Bedrock for AI-driven triage
        triage_data = _invoke_bedrock(structured_text)

        # Add FNOL ID and timestamp
        triage_data["fnol_id"] = _generate_fnol_id()
        triage_data["timestamp"] = datetime.now().isoformat() + "Z"

        # Enrich with handler details
        triage_data = _enrich_with_handler_details(triage_data)

        return json.dumps(triage_data, ensure_ascii=False, indent=2)

    except Exception as exc:
        # Graceful fallback on error
        fallback = {
            "fnol_id": _generate_fnol_id(),
            "timestamp": datetime.now().isoformat() + "Z",
            "detected_language": {"code": "EN", "name": "English", "confidence": 50},
            "claim_type": {
                "first_grouping": "System Error",
                "first_grouping_code": "ERR",
                "product_name": "Triage System Error",
                "product_code": "ERR-001",
                "display_format": "System Error – Triage System Error"
            },
            "severity": {
                "level": "Medium",
                "score": 50,
                "drivers": [
                    {"driver": "Automated triage system encountered an error", "impact": "High"},
                    {"driver": "Manual review required", "impact": "Medium"}
                ]
            },
            "key_signals_identified": [
                {"signal_type": "data_quality", "description": f"Triage error: {str(exc)[:80]}"}
            ],
            "decision_logic": {
                "summary": "System error prevented automated triage - escalating for manual review",
                "key_factors": [
                    "AI triage system encountered exception",
                    "Requires senior handler intervention"
                ]
            },
            "system_next_action": {
                "action": "Escalate to senior handler for manual triage",
                "rationale": "Automated system failed - human review needed"
            },
            "handler_next_action": {
                "action": "Review original FNOL text and perform manual triage",
                "priority": "Urgent"
            },
            "confidence": {
                "score": 0,
                "explanation": "No confidence due to system error",
                "factors_affecting": [
                    "Triage system exception",
                    f"Error: {str(exc)[:50]}"
                ]
            },
            "handlers": {
                "primary": {
                    "handler_id": "H-GL-002",
                    "name": "David Okonkwo",
                    "match_reason": "Global escalation for system error",
                    "contact_email": "d.okonkwo@nacora.com",
                    "contact_phone": "+44 20 1234 5632"
                },
                "secondary": null
            },
            "data_gaps": [],
            "financial": {"amount": None, "currency": None, "original_text": None},
            "geography": {
                "country": None,
                "country_name": None,
                "city": None,
                "region": "Global"
            },
            "policy": {"number": None, "type": None},
            "bms_integration": {
                "policy_number_field": "Links to existing policy record in NacoraHub",
                "handler_id_field": "Pre-fills Assigned To: H-GL-002 (David Okonkwo)",
                "product_code_field": "Maps to BMS product code ERR-001",
                "severity_field": "Sets SLA: Medium = 72h response (manual triage needed)"
            }
        }
        return json.dumps(fallback, ensure_ascii=False, indent=2)
