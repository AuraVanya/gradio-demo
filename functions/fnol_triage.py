import json
import os
import re
import time
from datetime import datetime
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
DEBUG_BEDROCK = os.getenv("DEBUG_BEDROCK", "false").lower() in ["1", "true", "yes"]

URGENCY_KEYWORDS = [
    "urgent",
    "asap",
    "immediately",
    "within 24",
    "within 48",
    "same day",
    "surveyor",
    "appointment",
    "expedite",
]

FIRE_KEYWORDS = ["fire", "smoke", "burn", "electrical fault", "sprinkler"]
THEFT_KEYWORDS = ["theft", "stolen", "missing", "pilferage", "burglary"]
WATER_KEYWORDS = ["water", "flood", "leak", "sprinkler discharge"]
TEMP_KEYWORDS = ["temperature", "cold chain", "refrigerated", "frozen", "spoilage"]
LIABILITY_KEYWORDS = ["third party", "liability", "injury", "bodily", "lawsuit", "claimant"]

REGION_KEYWORDS = {
    "EMEA": [
        "europe", "uk", "united kingdom", "germany", "france", "spain", "italy",
        "netherlands", "belgium", "hamburg", "london", "paris", "berlin", "dublin",
    ],
    "APAC": [
        "asia", "singapore", "hong kong", "china", "japan", "korea", "thailand",
        "malaysia", "indonesia", "vietnam", "australia", "sydney", "melbourne",
    ],
    "Americas": [
        "usa", "united states", "canada", "mexico", "brazil", "chile", "argentina",
        "new york", "los angeles", "houston", "miami", "toronto",
    ],
}

CURRENCY_SYMBOLS = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "¥": "JPY",
}

AMOUNT_PATTERN = re.compile(
    r"(?P<currency>EUR|USD|GBP|CHF|CAD|AUD|SGD|HKD|JPY|CNY|RMB|THB|MYR|IDR|INR|\$|€|£|¥)"
    r"\s*(?P<number>[0-9][0-9,\.\s]*)"
    r"\s*(?P<unit>million|m|billion|bn|b)?",
    re.IGNORECASE,
)


def _normalize_text(*parts):
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


def _textract_async_text(s3_key):
    response = textract_client.start_document_text_detection(
        DocumentLocation={
            "S3Object": {"Bucket": BUCKET_NAME, "Name": s3_key}
        }
    )
    job_id = response["JobId"]
    while True:
        result = textract_client.get_document_text_detection(JobId=job_id)
        status = result["JobStatus"]
        if status == "SUCCEEDED":
            break
        if status == "FAILED":
            raise RuntimeError("Textract job failed")
        time.sleep(2)

    blocks = result.get("Blocks", [])
    next_token = result.get("NextToken")
    while next_token:
        result = textract_client.get_document_text_detection(
            JobId=job_id,
            NextToken=next_token,
        )
        blocks.extend(result.get("Blocks", []))
        next_token = result.get("NextToken")

    lines = [block["Text"] for block in blocks if block.get("BlockType") == "LINE"]
    return "\n".join(lines)


def _textract_image_text(file_path):
    with open(file_path, "rb") as handle:
        image_bytes = handle.read()
    result = textract_client.detect_document_text(
        Document={"Bytes": image_bytes}
    )
    blocks = result.get("Blocks", [])
    lines = [block["Text"] for block in blocks if block.get("BlockType") == "LINE"]
    return "\n".join(lines)


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
        # Reuse ACORD Textract extraction to build key-value text when possible
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


def _extract_amount(text):
    match = AMOUNT_PATTERN.search(text)
    if not match:
        return None

    currency_raw = match.group("currency").upper()
    currency = CURRENCY_SYMBOLS.get(currency_raw, currency_raw)
    number_raw = match.group("number").replace(",", " ").replace(" ", "")
    try:
        number = float(number_raw)
    except ValueError:
        return None

    unit = (match.group("unit") or "").lower()
    multiplier = 1
    if unit in ["million", "m"]:
        multiplier = 1_000_000
    elif unit in ["billion", "bn", "b"]:
        multiplier = 1_000_000_000

    total = number * multiplier
    display = match.group(0).strip()
    return {
        "currency": currency,
        "amount": total,
        "display": display,
    }


def _detect_region(text):
    text_lower = text.lower()
    for region, keywords in REGION_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return region
    return "EMEA"


def _detect_claim_type(text):
    text_lower = text.lower()
    is_cargo = any(keyword in text_lower for keyword in [
        "cargo", "shipment", "consignee", "bill of lading", "warehouse", "bonded",
        "pallet", "freight", "transit", "consignment",
    ])
    is_marine = any(keyword in text_lower for keyword in [
        "marine", "ocean", "vessel", "port",
    ])
    is_liability = any(keyword in text_lower for keyword in LIABILITY_KEYWORDS)

    if is_cargo or is_marine:
        if is_liability:
            return "marine cargo liability"
        return "marine cargo"
    if is_liability:
        return "liability"
    return "other"


def _detect_subtype(text):
    text_lower = text.lower()
    if any(k in text_lower for k in FIRE_KEYWORDS):
        return "fire"
    if any(k in text_lower for k in THEFT_KEYWORDS):
        return "theft"
    if any(k in text_lower for k in WATER_KEYWORDS):
        return "water damage"
    if any(k in text_lower for k in TEMP_KEYWORDS):
        return "temperature breach"
    if "collision" in text_lower or "impact" in text_lower:
        return "collision/impact"
    return "general damage"


def _has_docs(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in [
        "attached", "report", "photos", "images", "invoice", "packing list", "bill of lading",
        "survey", "police report",
    ])


def _is_urgent(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in URGENCY_KEYWORDS)


def _build_severity(text, amount_info, urgent):
    text_lower = text.lower()
    factors = []
    score = 0
    critical_trigger = False

    if amount_info:
        display = amount_info["display"]
        currency = amount_info["currency"]
        factors.append(f"Estimated total value {currency} {display.replace(currency, '').strip()}")
        if amount_info["amount"] >= 5_000_000:
            score += 4
        elif amount_info["amount"] >= 1_000_000:
            score += 3
        elif amount_info["amount"] >= 250_000:
            score += 2
        else:
            score += 1

    if any(k in text_lower for k in FIRE_KEYWORDS):
        factors.append("Fire loss reported")
        score += 2

    if any(k in text_lower for k in TEMP_KEYWORDS):
        factors.append("Temperature breach indicates spoilage risk")
        score += 2

    if "total loss" in text_lower or "total losses" in text_lower:
        factors.append("Total loss reported on at least one shipment")
        score += 2

    if "multiple" in text_lower and any(k in text_lower for k in ["consignee", "shipment", "pallet", "consignment"]):
        factors.append("Multiple consignments affected")
        score += 1

    if urgent:
        factors.append("Urgent request for surveyor appointment or guidance")
        score += 1

    if "business interruption" in text_lower or "supply chain" in text_lower:
        factors.append("Potential business interruption or supply chain impact")
        score += 2

    if any(k in text_lower for k in ["injury", "fatal", "hospital"]):
        factors.append("Injury impact reported")
        score += 4
        critical_trigger = True

    if any(k in text_lower for k in ["lawsuit", "legal", "regulatory", "contractual" ]):
        factors.append("Legal or contractual exposure flagged")
        score += 3

    if not factors:
        factors.append("Limited loss detail provided")

    if critical_trigger or score >= 7:
        severity = "Critical"
    elif score >= 4:
        severity = "High"
    elif score >= 2:
        severity = "Medium"
    else:
        severity = "Low"

    return severity, factors


def _recommended_handler(claim_type, subtype, region):
    if "marine cargo" in claim_type:
        speciality = "Marine cargo"
        if subtype in ["fire", "water damage"]:
            speciality = "Warehouse/fire cargo"
        elif subtype == "temperature breach":
            speciality = "Cold-chain cargo"
        return {
            "name": f"{region} Cargo Desk",
            "role": "Senior Marine Cargo Claims Handler",
            "region": region,
            "speciality": speciality,
            "reason": f"Loss involves {claim_type} exposure with {subtype} damage in {region}.",
        }

    if claim_type == "liability":
        return {
            "name": f"{region} Liability Desk",
            "role": "Liability Claims Handler",
            "region": region,
            "speciality": "General liability",
            "reason": f"Liability indicators present for a loss in {region}.",
        }

    return {
        "name": f"{region} Claims Desk",
        "role": "Claims Handler",
        "region": region,
        "speciality": "General commercial",
        "reason": f"Claim appears to be non-specialty in {region}.",
    }


def _build_prompt(fnol_text):
    instructions = """
You are an expert insurance FNOL (First Notice of Loss) triage assistant.

Your task is to analyze an incoming loss notification and produce a structured triage decision that a broker or claims handler can act on immediately.

INSTRUCTIONS
- Classify the claim using real insurance categories
- Assess severity based on exposure, urgency, and risk
- Provide clear reasoning for severity
- Recommend the next action (not just classification)
- Recommend the most appropriate handler with justification

OUTPUT FORMAT (STRICT)
Return ONLY valid JSON. Do not include any text outside JSON.
Do NOT wrap the JSON in markdown code fences.

{
  "claim_type": "",
  "claim_subtype": "",
  "severity": "",
  "severity_factors": [],
  "recommended_action": "",
  "action_reasoning": "",
  "recommended_handler": {
    "name": "",
    "role": "",
    "region": "",
    "speciality": "",
    "reason": ""
  }
}

VALID VALUES
Claim Type:
- cargo
- marine
- liability
- other
- or combination like "marine cargo"

Severity:
- Low
- Medium
- High
- Critical

Recommended Action:
- assign_to_handler
- assign_to_handler_urgent
- escalate
- request_documentation
- reject

Decision Guidelines
- Always explain WHY in severity_factors with concrete details.
- High + urgent -> assign_to_handler_urgent
- Critical -> escalate
- Missing documents -> request_documentation
- Coverage issues -> reject
- Otherwise -> assign_to_handler

Action Reasoning must include:
- What to do next
- Time expectation if urgent
- What documents to review or request
- Any escalation requirement
"""
    return f"{instructions}\n\nINPUT:\n{fnol_text}\n"


def _bedrock_triage(fnol_text):
    prompt = _build_prompt(fnol_text)
    try:
        response = bedrock_runtime_client.invoke_model(
            modelId=INFERENCE_PROFILE_ARN,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1200,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }),
        )
    except Exception as exc:
        raise RuntimeError(f"Bedrock invoke_model failed: {exc}") from exc
    body = response.get("body")
    payload = body.read().decode("utf-8") if hasattr(body, "read") else body
    if not payload or not str(payload).strip():
        raise ValueError("Empty Bedrock response body. Check region/permissions.")

    text = ""
    try:
        result = json.loads(payload)
        if isinstance(result, dict):
            if "error" in result or "message" in result and "content" not in result:
                raise ValueError(f"Bedrock error: {result.get('error') or result.get('message')}")
            content = result.get("content")
            if isinstance(content, list) and content:
                text = content[0].get("text", "").strip()
            elif isinstance(result.get("completion"), str):
                text = result["completion"].strip()
            elif isinstance(result.get("output"), dict):
                output = result["output"]
                message = output.get("message", {})
                if isinstance(message, dict):
                    output_content = message.get("content", [])
                    if isinstance(output_content, list) and output_content:
                        text = output_content[0].get("text", "").strip()
            elif isinstance(result.get("generation"), str):
                text = result["generation"].strip()
    except json.JSONDecodeError:
        raise ValueError(f"Non-JSON response from Bedrock: {str(payload)[:200]}")

    if not text:
        raise ValueError(f"Unrecognized Bedrock response: {str(payload)[:200]}")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return JSON: {exc}. Raw: {cleaned[:200]}") from exc
    return cleaned


def triage_fnol(
    free_text,
    doc_file,
    insured_name,
    policy_number,
    location,
    estimated_value,
    urgency_notes,
    documents_list,
    extra_notes,
):
    doc_text = _extract_text_from_upload(doc_file)

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

    try:
        return _bedrock_triage(structured_text)
    except Exception as exc:
        debug_detail = ""
        if DEBUG_BEDROCK:
            debug_detail = f"Debug: {str(exc)}"
        fallback = {
            "claim_type": "other",
            "claim_subtype": "unparsed",
            "severity": "Medium",
            "severity_factors": [
                "Bedrock triage failed; returning fallback response",
                str(exc),
                debug_detail if debug_detail else None,
            ],
            "recommended_action": "request_documentation",
            "action_reasoning": "Re-run FNOL triage after confirming Bedrock credentials and policy data. Request incident report, photos, and shipment documents.",
            "recommended_handler": {
                "name": "EMEA Claims Desk",
                "role": "Claims Handler",
                "region": "EMEA",
                "speciality": "General commercial",
                "reason": "Fallback response due to Bedrock error.",
            },
        }
        fallback["severity_factors"] = [item for item in fallback["severity_factors"] if item]
        return json.dumps(fallback, ensure_ascii=True)
