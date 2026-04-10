"""
FNOL Triage JSON Output Schema - Business-Aligned Format
Enforces standardized, actionable, and transparent triage output
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class DetectedLanguage(BaseModel):
    code: str = Field(..., description="ISO language code (EN, DE, NL, etc.)")
    name: str = Field(..., description="Language name in English")
    confidence: int = Field(..., ge=0, le=100, description="Confidence percentage")


class ClaimType(BaseModel):
    """Standardized claim classification using approved taxonomy"""
    first_grouping: str = Field(..., description="Top-level category (e.g., Property, Liability)")
    first_grouping_code: str = Field(..., description="Category code (e.g., PROP, LIAB)")
    product_name: str = Field(..., description="Specific insurance product")
    product_code: str = Field(..., description="Product code (e.g., PROP-005)")
    display_format: str = Field(..., description="Display as 'First Grouping – Product Name'")


class SeverityDriver(BaseModel):
    """Individual factor explaining severity"""
    driver: str = Field(..., description="Clear, business-friendly explanation of severity factor")
    impact: Literal["High", "Medium", "Low"] = Field(..., description="Impact level of this driver")


class Severity(BaseModel):
    """Severity assessment with explainability"""
    level: Literal["Low", "Medium", "High", "Critical"] = Field(..., description="Severity level")
    score: int = Field(..., ge=0, le=100, description="Numeric severity score")
    drivers: List[SeverityDriver] = Field(
        ...,
        min_items=2,
        max_items=4,
        description="2-4 bullet points explaining WHY this severity was assigned"
    )


class SignalIdentified(BaseModel):
    """Key information extracted from claim input"""
    signal_type: Literal[
        "document_type",
        "financial_indicator",
        "incident_severity",
        "data_quality",
        "policy_type",
        "geographic_marker",
        "other"
    ] = Field(..., description="Type of signal")
    description: str = Field(..., description="User-friendly description (e.g., 'Lab report detected')")


class DecisionLogic(BaseModel):
    """Simple explanation of triage decision"""
    summary: str = Field(..., description="One-sentence decision summary")
    key_factors: List[str] = Field(
        ...,
        min_items=1,
        max_items=3,
        description="1-3 factors that led to this classification"
    )


class SystemNextAction(BaseModel):
    """System-level recommended action"""
    action: str = Field(..., description="What should happen next in the workflow")
    rationale: str = Field(..., description="Why this action is recommended")


class HandlerNextAction(BaseModel):
    """User-level handler recommendation"""
    action: str = Field(..., description="What the claims handler should do")
    priority: Literal["Immediate", "Urgent", "Standard", "Low"] = Field(..., description="Action priority")


class Handler(BaseModel):
    handler_id: str = Field(..., description="Handler ID (e.g., H-DACH-001)")
    name: str = Field(..., description="Handler full name")
    match_reason: str = Field(..., description="Why this handler was selected")
    contact_email: Optional[str] = Field(None, description="Handler email")
    contact_phone: Optional[str] = Field(None, description="Handler phone")


class Handlers(BaseModel):
    primary: Handler = Field(..., description="Primary handler")
    secondary: Optional[Handler] = Field(None, description="Secondary handler if needed")


class DataGap(BaseModel):
    field: str = Field(..., description="Missing field name")
    prompt: str = Field(..., description="User-facing prompt")
    importance: Literal["Critical", "High", "Medium", "Low"] = Field(
        ...,
        description="How important is this missing data"
    )


class ConfidenceScore(BaseModel):
    """Overall confidence with explanation"""
    score: int = Field(..., ge=0, le=100, description="Confidence percentage")
    explanation: str = Field(..., description="Short explanation (e.g., 'High confidence due to complete documentation')")
    factors_affecting: List[str] = Field(
        ...,
        max_items=3,
        description="Max 3 factors affecting confidence"
    )


class Financial(BaseModel):
    amount: Optional[float] = Field(None, description="Numeric amount")
    currency: Optional[str] = Field(None, description="Currency code (USD, EUR, etc.)")
    original_text: Optional[str] = Field(None, description="Original text from claim")


class Geography(BaseModel):
    country: Optional[str] = Field(None, description="ISO country code")
    country_name: Optional[str] = Field(None, description="Country name")
    city: Optional[str] = Field(None, description="City or port")
    region: Optional[str] = Field(None, description="Routing region")


class Policy(BaseModel):
    number: Optional[str] = Field(None, description="Policy number")
    type: Optional[str] = Field(None, description="Policy type if detected")


class BMSIntegration(BaseModel):
    """BMS field mappings for integration"""
    policy_number_field: str = Field(..., description="How policy # maps to BMS")
    handler_id_field: str = Field(..., description="How handler maps to BMS")
    product_code_field: str = Field(..., description="How product code maps to BMS")
    severity_field: str = Field(..., description="How severity sets SLA")


class FNOLTriageOutput(BaseModel):
    """
    Complete FNOL triage output - Business-aligned format

    Enforces:
    - Standardized claim type classification
    - Explainable severity scoring
    - Actionable recommendations
    - Transparent reasoning
    - Clear information hierarchy
    """
    fnol_id: str = Field(..., description="Generated FNOL ID (FNOL-YYMMDD-NNNN)")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    detected_language: DetectedLanguage = Field(..., description="Input language detection")

    # PRIMARY OUTPUT FIELDS (Priority 1)
    claim_type: ClaimType = Field(..., description="Standardized claim classification")
    severity: Severity = Field(..., description="Severity with drivers")
    system_next_action: SystemNextAction = Field(..., description="Recommended system workflow action")
    handler_next_action: HandlerNextAction = Field(..., description="Recommended handler action")

    # SUPPORTING EVIDENCE (Priority 2)
    key_signals_identified: List[SignalIdentified] = Field(
        ...,
        min_items=1,
        description="Key information extracted from input"
    )
    decision_logic: DecisionLogic = Field(..., description="Simple explanation of decision")
    confidence: ConfidenceScore = Field(..., description="Overall confidence with explanation")

    # HANDLER ROUTING (Priority 3)
    handlers: Handlers = Field(..., description="Handler recommendations")

    # DATA QUALITY (Priority 4)
    data_gaps: List[DataGap] = Field(..., description="Missing information with importance")

    # ADDITIONAL CONTEXT (Priority 5)
    financial: Financial = Field(..., description="Financial information")
    geography: Geography = Field(..., description="Geographic information")
    policy: Policy = Field(..., description="Policy information")
    bms_integration: BMSIntegration = Field(..., description="BMS field mappings")
