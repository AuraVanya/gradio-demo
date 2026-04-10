"""
FNOL Triage JSON Output Schema
Complete schema matching the specification in Section 10
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class DetectedLanguage(BaseModel):
    code: str = Field(..., description="ISO language code (EN, DE, NL, etc.)")
    name: str = Field(..., description="Language name in English")
    confidence: int = Field(..., ge=0, le=100, description="Confidence percentage")


class Classification(BaseModel):
    lob_code: str = Field(..., description="Line of business code from taxonomy")
    lob_display_name: str = Field(..., description="Display name in English")
    lob_local_name: str = Field(..., description="Local language name")
    lob_local_language: str = Field(..., description="Local language code")
    insurance_product: str = Field(..., description="Specific product under the LoB")
    confidence: int = Field(..., ge=0, le=100, description="Classification confidence")
    reasoning: str = Field(..., description="Why this classification was chosen")


class SeverityFactor(BaseModel):
    text: str = Field(..., description="Factor description")
    weight: Literal["primary", "secondary", "minor"] = Field(..., description="Factor weight")


class Severity(BaseModel):
    level: Literal["Low", "Medium", "High", "Critical"] = Field(..., description="Severity level")
    score: int = Field(..., ge=0, le=100, description="Numeric severity score")
    confidence: int = Field(..., ge=0, le=100, description="Confidence in assessment")
    factors: List[SeverityFactor] = Field(..., description="Ordered list of severity factors")


class Financial(BaseModel):
    amount: Optional[float] = Field(None, description="Numeric amount")
    currency: Optional[str] = Field(None, description="Currency code (USD, EUR, etc.)")
    original_text: Optional[str] = Field(None, description="Original text from claim")
    confidence: int = Field(..., ge=0, le=100, description="Detection confidence")


class Geography(BaseModel):
    country: Optional[str] = Field(None, description="ISO country code")
    country_name: Optional[str] = Field(None, description="Country name")
    city: Optional[str] = Field(None, description="City or port")
    specific_location: Optional[str] = Field(None, description="Warehouse, vessel, road")
    region: Optional[str] = Field(None, description="Routing region")
    confidence: int = Field(..., ge=0, le=100, description="Detection confidence")


class Policy(BaseModel):
    number: Optional[str] = Field(None, description="Policy number")
    confidence: int = Field(..., ge=0, le=100, description="Detection confidence")


class RecommendedAction(BaseModel):
    action: Literal[
        "assign_to_handler",
        "assign_to_handler_urgent",
        "escalate",
        "request_documentation",
        "request_survey",
        "reject"
    ] = Field(..., description="Action code")
    label: str = Field(..., description="Human-readable action label")
    reasoning: str = Field(..., description="Full reasoning for this action")
    steps: List[str] = Field(..., description="Concrete next steps")


class Handler(BaseModel):
    handler_id: str = Field(..., description="Handler ID (e.g., H-DACH-001)")
    match_reason: str = Field(..., description="Why this handler was selected")
    role_in_claim: Optional[str] = Field(None, description="Role for secondary handler")


class Handlers(BaseModel):
    primary: Handler = Field(..., description="Primary handler")
    secondary: Optional[Handler] = Field(None, description="Secondary handler if needed")


class DataGap(BaseModel):
    field: str = Field(..., description="Missing field name")
    prompt: str = Field(..., description="User-facing prompt")


class RiskFlag(BaseModel):
    flag: str = Field(..., description="Risk flag text")
    severity: Literal["high", "medium", "low"] = Field(..., description="Flag severity")


class ReasoningTrace(BaseModel):
    chain: List[str] = Field(..., description="Numbered reasoning steps")
    risk_flags: List[RiskFlag] = Field(..., description="Identified risk flags")
    confidence_overall: int = Field(..., ge=0, le=100, description="Overall confidence")
    ai_deductions: List[str] = Field(..., description="AI inferences beyond explicit input")


class BMSIntegration(BaseModel):
    policy_number_field: str = Field(..., description="How policy # maps to BMS")
    handler_id_field: str = Field(..., description="How handler maps to BMS")
    lob_code_field: str = Field(..., description="How LoB maps to BMS")
    severity_field: str = Field(..., description="How severity sets SLA")
    financial_field: str = Field(..., description="How amount pre-fills loss")
    open_cover_flag: str = Field(..., description="How open cover triggers module")


class FNOLTriageOutput(BaseModel):
    """Complete FNOL triage output matching Section 10 schema"""
    fnol_id: str = Field(..., description="Generated FNOL ID (FNOL-YYMMDD-NNNN)")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    detected_language: DetectedLanguage = Field(..., description="Input language detection")
    classification: Classification = Field(..., description="Claim type classification")
    severity: Severity = Field(..., description="Severity assessment")
    financial: Financial = Field(..., description="Financial information")
    geography: Geography = Field(..., description="Geographic information")
    policy: Policy = Field(..., description="Policy information")
    recommended_action: RecommendedAction = Field(..., description="Next action recommendation")
    handlers: Handlers = Field(..., description="Handler recommendations")
    data_gaps: List[DataGap] = Field(..., description="Missing information")
    reasoning_trace: ReasoningTrace = Field(..., description="AI reasoning transparency")
    bms_integration: BMSIntegration = Field(..., description="BMS field mappings")
