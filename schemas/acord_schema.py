from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal

# Pydantic Schema

transaction_status_options = Literal["QUOTE", "ISSUE POLICY", "RENEW", "CHANGE", "REWRITE", "REMARKET", "CANCEL"]
billing_plan_options = Literal["DIRECT", "AGENCY", "OTHER"]
entity_type_options = Literal["CORPORATION", "LLC", "PARTNERSHIP", "INDIVIDUAL", "SOLE PROPRIETOR", "JOINT VENTURE", "NON-PROFIT", "OTHER"]
city_limits_options = Literal["INSIDE", "OUTSIDE"]
applicant_type_options = Literal["OWNER", "MANAGER", "OFFICER", "PARTNER", "OTHER"]
phone_type_options = Literal["HOME", "BUS", "CELL", "FAX"]
interest_options = Literal["OWNER", "TENANT", "LESSEE", "OTHER"]
additional_interest_type_options = Literal["MORTGAGEE", "LOSS PAYEE", "LIENHOLDER", "ADDITIONAL INSURED", "CERTIFICATE HOLDER", "OTHER"]
evidence_options = Literal["CERTIFICATE", "POLICY", "BOTH"]

class Header(BaseModel):
    application_date: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$", description="Application date in MM/DD/YYYY format")
    policy_number: Optional[str] = Field(None, description="Policy number if applicable")
    agency_customer_id: Optional[str] = Field(None, description="Agency's customer identification number")

class AgencyInfo(BaseModel):
    name: Optional[str] = Field(None, description="Agency name")
    contact_name: Optional[str] = Field(None, description="Primary agency contact person")
    phone: Optional[str] = Field(None, description="Agency phone number with optional extension")
    email: Optional[EmailStr] = Field(None, description="Agency email address")

class CarrierInfo(BaseModel):
    name: Optional[str] = Field(None, description="Carrier/company name")
    naic_code: Optional[str] = Field(None, description="NAIC code in digit")
    program_name: Optional[str] = Field(None, description="Company policy or program name")
    program_code: Optional[str] = Field(None, description="Program code identifier")
    underwriter: Optional[str] = Field(None, description="Assigned underwriter name")

class TransactionInfo(BaseModel):
    status: Optional[transaction_status_options] = Field(None, description="Current transaction status")
    code: Optional[str] = Field(None, description="Transaction code")
    subcode: Optional[str] = Field(None, description="Transaction subcode")
    effective_date_time: Optional[str] = Field(None, description="Effective date and time for bound/changed policies")

class LineOfBusiness(BaseModel):
    line_name: Optional[str] = Field(None, description="Line of business name")
    premium: Optional[float] = Field(None, ge=0, description="Premium amount for this line")

class PolicyTerm(BaseModel):
    effective_date: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$", description="Proposed effective date")
    expiration_date: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$", description="Proposed expiration date")
    billing_plan: Optional[billing_plan_options] = Field(None, description="Billing arrangement")
    payment_plan: Optional[str] = Field(None, description="Payment schedule (e.g., ANNUAL, MONTHLY)")
    method_of_payment:  Optional[str] = Field(None, description="Payment method")
    audit: Optional[str] = Field(None, description="Audit method if applicable")
    deposit: Optional[float] = Field(None, ge=0, description="Deposit premium amount")
    minimum_premium: Optional[float] = Field(None, ge=0, description="Minimum premium amount")
    total_policy_premium: Optional[float] = Field(None, ge=0, description="Total policy premium")

class NamedInsured(BaseModel):
    name: str = Field(..., description="Legal name of insured entity or individual")
    mailing_address: Optional[str] = Field(None, description="Complete mailing address")
    business_phone: Optional[str] = Field(None, description="Business phone number")
    website: Optional[str] = Field(None, description="Business website URL")
    entity_type: Optional[entity_type_options] = Field(None, description="Legal entity type")
    fein_or_ssn: Optional[str] = Field(None, pattern=r"^\d{2}-?\d{7}|\d{3}-?\d{2}-?\d{4}$", description="Federal Employer ID or Social Security Number")
    gl_code: Optional[str] = Field(None, description="General liability classification code")
    sic_code: Optional[str] = Field(None, description="Standard Industrial Classification code in digit")
    naics_code: Optional[str] = Field(None, description="North American Industry Classification code in digit")

class ApplicantContact(BaseModel):
    type: Optional[applicant_type_options] = Field(None, description="Contact's role/relationship")
    name: Optional[str] = Field(None, description="Contact person's full name")
    phone_type: Optional[phone_type_options] = Field(None, description="Phone type")
    phone: Optional[str] = Field(None, description="Primary phone number")
    email: Optional[EmailStr] = Field(None, description="Primary email address")

class PremiseInformation(BaseModel):
    location_number: Optional[str] = Field(None, description="Location identifier")
    building_number: Optional[str] = Field(None, description="Building identifier")
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, pattern=r"^[A-Z]{2}$", description="Two-letter state code")
    zip: Optional[str] = Field(None, pattern=r"^\d{5}(-\d{4})?$", description="ZIP code")
    county: Optional[str] = Field(None, description="County name")
    city_limits: Optional[city_limits_options] = Field(None, description="Location relative to city limits")
    interest: Optional[interest_options] = Field(None, description="Applicant's interest in the property")
    num_employees_full_time: Optional[int] = Field(None, ge=0, description="Number of full-time employees")
    num_employees_part_time: Optional[int] = Field(None, ge=0, description="Number of part-time employees")
    annual_revenues: Optional[float] = Field(None, ge=0, description="Annual revenues at this location")
    occupied_area_sq_ft: Optional[float] = Field(None, ge=0, description="Square footage occupied by applicant")
    open_to_public_area_sq_ft: Optional[float] = Field(None, ge=0, description="Square footage open to the public")
    total_building_area_sq_ft: Optional[float] = Field(None, ge=0, description="Total building square footage")
    description_of_operations: Optional[str] = Field(None, description="Detailed description of business operations at this location")
    leased_to_others: Optional[bool] = Field(None, description="Whether any area is leased to other parties")

class BusinessDescription(BaseModel):
    nature_of_business: Optional[str] = Field(None, description="Primary business type or industry")
    date_business_started: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$", description="Date business commenced operations")
    description_primary_operations: Optional[str] = Field(None, description="Detailed description of primary business operations")
    description_other_named_insured_ops: Optional[str] = Field(None, description="Operations description for other named insureds")

class InterestInItem(BaseModel):
    location: Optional[str] = Field(None, description="Location identifier")
    building: Optional[str] = Field(None, description="Building identifier")
    vehicle: Optional[str] = Field(None, description="Vehicle identifier")
    item_description: Optional[str] = Field(None, description="Description of specific item")

class AdditionalInterest(BaseModel):
    interest_type: Optional[additional_interest_type_options] = Field(None, description="Type of interest")
    name_and_address: Optional[str] = Field(None, description="Complete name and address of interested party")
    rank: Optional[str] = Field(None, description="Priority ranking (e.g., 1st, 2nd)")
    evidence: Optional[evidence_options] = Field(None, description="Type of evidence to be provided")
    send_bill: Optional[bool] = Field(None, description="Whether to send billing to this party")
    interest_in_item: Optional[InterestInItem] = Field(None, description="Specific item(s) the interest applies to")
    reference_loan_number: Optional[str] = Field(None, description="Reference or loan number")
    lien_amount: Optional[float] = Field(None, ge=0, description="Amount of lien or loan")
    reason_for_interest: Optional[str] = Field(None, description="Explanation of why interest is required")
    interest_end_date: Optional[str] = Field(None, description="Date when interest terminates")

class SubsidiaryDetails(BaseModel):
    parent_name: Optional[str] = Field(None, description="Parent company name")
    relationship: Optional[str] = Field(None, description="Nature of relationship")
    percent_owned: Optional[float] = Field(None, ge=0, le=100, description="Percentage owned by parent")

class SafetyProgramDetails(BaseModel):
    safety_manual: Optional[bool] = Field(None, description="Written safety manual exists")
    safety_position: Optional[bool] = Field(None, description="Designated safety position exists")
    monthly_meetings: Optional[bool] = Field(None, description="Monthly safety meetings held")
    osha: Optional[bool] = Field(None, description="OSHA compliance program")

class GeneralInformation(BaseModel):
    is_subsidiary: Optional[bool] = Field(None, description="Is applicant a subsidiary of another entity?")
    subsidiary_details: Optional[SubsidiaryDetails] = Field(None, description="Details if applicant is a subsidiary")
    has_subsidiaries: Optional[bool] = Field(None, description="Does applicant have any subsidiaries?")
    formal_safety_program: Optional[bool] = Field(None, description="Is a formal safety program in operation?")
    safety_program_details: Optional[SafetyProgramDetails] = Field(None, description="Safety program components")
    flammables_exposure: Optional[bool] = Field(None, description="Any exposure to flammables, explosives, or chemicals?")
    other_insurance_with_company: Optional[bool] = Field(None, description="Any other insurance with this company?")
    policy_declined_cancelled_nonrenewed: Optional[bool] = Field(None, description="Any policy declined, cancelled, or non-renewed in past 3 years?")
    past_losses_abuse_discrimination: Optional[bool] = Field(None, description="Any past losses/claims for sexual abuse, discrimination, or wrongful hiring?")
    convicted_of_fraud_arson: Optional[bool] = Field(None, description="Any applicant convicted of fraud, bribery, or arson?")
    uncorrected_fire_safety_violations: Optional[bool] = Field(None, description="Any uncorrected fire/safety code violations?")
    foreclosure_bankruptcy_last_5_years: Optional[bool] = Field(None, description="Foreclosure, repossession, or bankruptcy in last 5 years?")
    judgement_lien_last_5_years: Optional[bool] = Field(None, description="Judgement or lien in last 5 years?")
    business_in_trust: Optional[bool] = Field(None, description="Has business been placed in a trust?")
    trust_name: Optional[str] = Field(None, description="Name of trust if applicable")
    foreign_operations: Optional[bool] = Field(None, description="Any foreign operations or exposures?")
    other_business_ventures_not_covered: Optional[bool] = Field(None, description="Other business ventures not requesting coverage?")
    owns_operates_drones: Optional[bool] = Field(None, description="Does applicant own/lease/operate drones?")
    hires_drone_operators: Optional[bool] = Field(None, description="Does applicant hire others to operate drones?")
    remarks: Optional[str] = Field(None, description="Additional remarks or processing instructions")

class PriorCarrier(BaseModel):
    year_label: Optional[str] = Field(None, description="Time period identifier")
    general_liability_carrier: Optional[str] = Field(None, description="GL carrier name")
    general_liability_policy_number: Optional[str] = Field(None, description="GL policy number")
    general_liability_premium: Optional[float] = Field(None, ge=0, description="GL premium amount")
    automobile_carrier: Optional[str] = Field(None, description="Auto carrier name")
    automobile_policy_number: Optional[str] = Field(None, description="Auto policy number")
    automobile_premium: Optional[float] = Field(None, ge=0, description="Auto premium amount")
    property_carrier: Optional[str] = Field(None, description="Property carrier name")
    property_policy_number: Optional[str] = Field(None, description="Property policy number")
    property_premium: Optional[float] = Field(None, ge=0, description="Property premium amount")
    other_carrier: Optional[str] = Field(None, description="Other coverage carrier name")
    other_policy_number: Optional[str] = Field(None, description="Other coverage policy number")
    other_premium: Optional[float] = Field(None, ge=0, description="Other coverage premium amount")
    effective_date: Optional[str] = Field(None, description="Policy effective date")
    expiration_date: Optional[str] = Field(None, description="Policy expiration date")

class Loss(BaseModel):
    date_of_occurrence: Optional[str] = Field(None, description="Date loss occurred")
    line_of_business: Optional[str] = Field(None, description="Type of coverage (GL, Auto, Property, etc.)")
    description: Optional[str] = Field(None, description="Description of loss event")
    date_of_claim: Optional[str] = Field(None, description="Date claim was filed")
    amount_paid: Optional[float] = Field(None, ge=0, description="Amount paid to date")
    amount_reserved: Optional[float] = Field(None, ge=0, description="Amount reserved for future payment")
    subrogation: Optional[bool] = Field(None, description="Subrogation pursued or available")
    claim_open: Optional[bool] = Field(None, description="Whether claim is still open")

class LossHistory(BaseModel):
    no_losses: Optional[bool] = Field(None, description="Check if no losses in specified period")
    years_checked: Optional[int] = Field(None, ge=1, le=10, description="Number of years of loss history reviewed")
    total_losses_amount: Optional[float] = Field(None, ge=0, description="Total dollar amount of all losses")
    losses: Optional[List[Loss]] = Field(None, description="Individual loss details")

class SignatureInfo(BaseModel):
    privacy_notice_given: Optional[bool] = Field(None, description="Privacy notice provided to applicant")
    applicant_initials: Optional[str] = Field(None, description="Applicant's initials acknowledging notice")
    producer_signature: Optional[str] = Field(None, description="Producer's signature")
    producer_name: Optional[str] = Field(None, description="Producer's printed name")
    applicant_signature: Optional[str] = Field(None, description="Applicant's signature")
    date: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$", description="Signature date")
    state_producer_license_no: Optional[str] = Field(None, description="Producer's state license number")
    national_producer_number: Optional[str] = Field(None, description="Producer's NPN number")

class ACORD125Schema(BaseModel):
    header: Optional[Header] = None
    agency_info: Optional[AgencyInfo] = None
    carrier_info: Optional[CarrierInfo] = None
    transaction_info: Optional[TransactionInfo] = None
    lines_of_business: Optional[List[LineOfBusiness]] = None
    attachments: Optional[List[str]] = None
    policy_term: PolicyTerm
    named_insureds: List[NamedInsured] = Field(..., min_length=1)
    applicant_contact: Optional[ApplicantContact] = None
    premises_information: Optional[List[PremiseInformation]] = None
    business_description: Optional[BusinessDescription] = None
    additional_interests: Optional[List[AdditionalInterest]] = None
    general_information: Optional[GeneralInformation] = None
    prior_carriers: Optional[List[PriorCarrier]] = None
    loss_history: Optional[LossHistory] = None
    signature_info: Optional[SignatureInfo] = None

    class Config:
        extra = "forbid"
