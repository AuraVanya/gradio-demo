import json
import gradio as gr
from functions.fnol_triage import triage_fnol
from datetime import datetime

# Load form configuration
with open("data/form_config.json", "r") as f:
    FORM_CONFIG = json.load(f)

# Load country mapping
with open("data/country_region_mapping.json", "r") as f:
    COUNTRY_DATA = json.load(f)

# Load product taxonomy
with open("data/nacora_product_taxonomy.json", "r") as f:
    PRODUCT_TAX = json.load(f)

# Prepare dropdown choices
COUNTRY_CHOICES = [(f"{code} - {name}", code) for code, name in FORM_CONFIG["countries"].items()]
CURRENCY_CHOICES = FORM_CONFIG["currencies"]

# Flatten incident types for dropdown
INCIDENT_TYPE_CHOICES = []
for category, incidents in FORM_CONFIG["incident_types"].items():
    for incident in incidents:
        INCIDENT_TYPE_CHOICES.append(f"{category}: {incident}")

# Flatten product taxonomy for dropdown
PRODUCT_CHOICES = []
for cat in PRODUCT_TAX["categories"]:
    for prod in cat["products"]:
        PRODUCT_CHOICES.append(f"{cat['first_grouping']} – {prod['product_name']}")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@600;700&display=swap');

:root {
  --ink: #0f172a;
  --ink-soft: #334155;
  --muted: #64748b;
  --muted-light: #94a3b8;
  --panel: #ffffff;
  --panel-soft: #f8fafc;
  --line: #e2e8f0;
  --line-soft: #f1f5f9;
  --accent: #0f172a;
  --bg: #f4f6f9;
  --green-text: #166534;
  --green-border: #16a34a;
  --green-bg: #f0fdf4;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 18px;
  --radius-pill: 999px;
}

/* ─── kill the orange ─── */
:root, .gradio-container {
  --color-accent: #334155 !important;
  --color-accent-soft: #f1f5f9 !important;
  --slider-color: #334155 !important;
  --checkbox-label-gap: 8px;
}

*, *::before, *::after { box-sizing: border-box; }

/* override focus rings on all inputs / textareas */
.gradio-container input:focus,
.gradio-container textarea:focus,
.gradio-container select:focus {
  outline: none !important;
  box-shadow: 0 0 0 2px #cbd5e1 !important;
  border-color: #94a3b8 !important;
}

/* Gradio wraps textboxes in a span that also gets an orange outline */
.gradio-container .block:focus-within {
  box-shadow: none !important;
}

body, .gradio-container {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--ink);
  font-size: 14px;
}

/* ─── shell ─── */
.fnol-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 4px;
}

/* ─── hero ─── */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 0 16px;
}

.hero-left {}

.hero-title {
  font-family: "Space Grotesk", sans-serif;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ink);
  margin: 0 0 6px;
  line-height: 1.2;
}

.hero-title p { margin: 0; }

.hero-subtitle {
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.6;
  max-width: 500px;
}

.hero-subtitle p { margin: 0; }

/* live demo badge — white bg, green text, green border */
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #ffffff;
  color: var(--green-text);
  border: 1.5px solid var(--green-border);
  padding: 8px 14px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
  width: fit-content;
}

/* green pulse dot */
.hero-badge::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--green-border);
  flex-shrink: 0;
}

/* ─── section labels ─── */
.label {
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  font-weight: 600;
  margin: 0 0 10px;
}

/* ─── panels ─── */
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: 0 1px 3px rgba(15,23,42,0.06), 0 8px 24px -12px rgba(15,23,42,0.12);
}

.panel-soft {
  background: var(--panel-soft);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 14px;
}

/* ─── chips / sample buttons ─── */
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}

.chip-row button {
  border-radius: var(--radius-pill) !important;
  border: 1px solid var(--line) !important;
  background: var(--panel-soft) !important;
  color: var(--ink-soft) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  padding: 5px 12px !important;
  height: auto !important;
  min-height: unset !important;
  line-height: 1.4 !important;
  white-space: nowrap !important;
  transition: background 0.15s, border-color 0.15s !important;
}

.chip-row button:hover {
  background: var(--line-soft) !important;
  border-color: var(--muted-light) !important;
}

/* ─── run / clear buttons ─── */
.run-btn button {
  background: var(--ink) !important;
  color: #fff !important;
  border-radius: var(--radius-pill) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  padding: 9px 22px !important;
  border: none !important;
  transition: opacity 0.15s !important;
}

.run-btn button:hover { opacity: 0.85 !important; }

.ghost-btn button {
  border-radius: var(--radius-pill) !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  color: var(--muted) !important;
  border: 1px solid var(--line) !important;
  background: transparent !important;
  padding: 9px 18px !important;
  transition: background 0.15s !important;
}

.ghost-btn button:hover {
  background: var(--panel-soft) !important;
}

/* ─── tabs ─── */
.gradio-container .tabs > .tab-nav {
  border-bottom: 1px solid var(--line) !important;
  gap: 0 !important;
}

.gradio-container .tabs > .tab-nav button {
  font-weight: 500 !important;
  font-size: 13px !important;
  color: var(--muted) !important;
  padding: 8px 14px !important;
  border-radius: 0 !important;
  border: none !important;
  background: transparent !important;
}

.gradio-container .tabs > .tab-nav button.selected {
  color: var(--ink) !important;
  border-bottom: 2px solid var(--ink) !important;
  font-weight: 600 !important;
}

/* ─── output cards ─── */
.card {
  background: var(--panel-soft);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  transition: border-color 0.15s;
}

.card:focus-within {
  border-color: var(--muted-light);
}

.card label {
  color: var(--muted) !important;
  font-size: 11px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  font-weight: 600 !important;
  margin-bottom: 4px !important;
}

.card textarea,
.card input {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  font-weight: 500 !important;
  font-size: 13.5px !important;
  color: var(--ink) !important;
  padding: 0 !important;
}

/* ─── misc ─── */
.small-note {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

/* tighten row gaps */
.gradio-container .gap {
  gap: 12px !important;
}
"""


def construct_loss_description_from_form(
    policy_number, insured_name, date_of_loss, time_of_loss,
    country, city, address, product_type, incident_type,
    loss_description, estimated_value, currency,
    # Motor conditional
    vehicle_plate, vehicle_model, driver_name,
    # Property conditional
    property_type, damage_type,
    # Health conditional
    hospital_name, treatment_type,
    # Marine conditional
    vessel_name, bill_of_lading,
):
    """Constructs structured loss description from form inputs"""
    parts = []

    # Policy & Insured
    if policy_number:
        parts.append(f"Policy Number: {policy_number}")
    if insured_name:
        parts.append(f"Insured: {insured_name}")

    # Product Type
    if product_type and product_type != "Unknown / Let AI Detect":
        parts.append(f"Insurance Product: {product_type}")

    # Date & Time
    if date_of_loss:
        parts.append(f"Date of Loss: {date_of_loss}")
    if time_of_loss and time_of_loss != "Unknown":
        parts.append(f"Time of Loss: {time_of_loss}")

    # Location
    location_parts = []
    if city:
        location_parts.append(city)
    if country:
        country_name = FORM_CONFIG["countries"].get(country, country)
        location_parts.append(country_name)
    if location_parts:
        parts.append(f"Location: {', '.join(location_parts)}")
    if address:
        parts.append(f"Address: {address}")

    # Incident Type
    if incident_type:
        parts.append(f"Incident Type: {incident_type}")

    # Loss Description (required field)
    if loss_description:
        parts.append(f"\nDescription:\n{loss_description}")

    # Financial
    if estimated_value:
        parts.append(f"\nEstimated Loss: {currency} {estimated_value:,.2f}" if isinstance(estimated_value, (int, float)) else f"\nEstimated Loss: {currency} {estimated_value}")

    # Conditional fields
    if vehicle_plate or vehicle_model or driver_name:
        motor_info = []
        if vehicle_plate:
            motor_info.append(f"Vehicle Plate: {vehicle_plate}")
        if vehicle_model:
            motor_info.append(f"Vehicle Model: {vehicle_model}")
        if driver_name:
            motor_info.append(f"Driver: {driver_name}")
        if motor_info:
            parts.append("\n--- Motor Details ---")
            parts.extend(motor_info)

    if property_type or damage_type:
        prop_info = []
        if property_type:
            prop_info.append(f"Property Type: {property_type}")
        if damage_type:
            prop_info.append(f"Damage Type: {damage_type}")
        if prop_info:
            parts.append("\n--- Property Details ---")
            parts.extend(prop_info)

    if hospital_name or treatment_type:
        health_info = []
        if hospital_name:
            health_info.append(f"Hospital: {hospital_name}")
        if treatment_type:
            health_info.append(f"Treatment: {treatment_type}")
        if health_info:
            parts.append("\n--- Health Details ---")
            parts.extend(health_info)

    if vessel_name or bill_of_lading:
        marine_info = []
        if vessel_name:
            marine_info.append(f"Vessel: {vessel_name}")
        if bill_of_lading:
            marine_info.append(f"B/L Reference: {bill_of_lading}")
        if marine_info:
            parts.append("\n--- Marine Details ---")
            parts.extend(marine_info)

    return "\n".join(parts)


def triage_and_parse(
    # Free text (legacy)
    free_text,
    doc_file,
    # New structured form fields
    policy_number, insured_name, date_of_loss, time_of_loss,
    country, city, address, product_type, incident_type,
    loss_description, estimated_value, currency,
    # Conditional fields
    vehicle_plate, vehicle_model, driver_name,
    property_type, damage_type,
    hospital_name, treatment_type,
    vessel_name, bill_of_lading,
):
    """Main triage function handling both free-text and structured form inputs"""

    # Determine input mode
    if free_text and free_text.strip():
        # Free text mode (legacy)
        input_text = free_text
    elif loss_description and loss_description.strip():
        # Structured form mode - construct description
        input_text = construct_loss_description_from_form(
            policy_number, insured_name, date_of_loss, time_of_loss,
            country, city, address, product_type, incident_type,
            loss_description, estimated_value, currency,
            vehicle_plate, vehicle_model, driver_name,
            property_type, damage_type,
            hospital_name, treatment_type,
            vessel_name, bill_of_lading,
        )
    else:
        # Empty input
        input_text = ""

    # Call triage function (with legacy signature for backward compatibility)
    json_str = triage_fnol(
        input_text,
        doc_file,
        "", "", "", "", "", "", ""  # Empty legacy fields
    )

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return json_str, "", "", "", "", "", "", "", "", "", "", ""

    # === 1. CLAIM TYPE (Top Priority) ===
    claim_type_data = data.get("claim_type", {})
    claim_type = claim_type_data.get("display_format", "Unknown")

    # === 2. SEVERITY (with drivers) ===
    severity_data = data.get("severity", {})
    severity_level = severity_data.get("level", "")
    severity_score = severity_data.get("score", 0)
    severity_display = f"{severity_level} ({severity_score}/100)"

    # Severity drivers with impact levels
    severity_drivers = severity_data.get("drivers", [])
    drivers_text = "\n".join([
        f"• {driver.get('driver', '')} [{driver.get('impact', '').upper()}]"
        for driver in severity_drivers
    ])

    # === 3. KEY SIGNALS IDENTIFIED ===
    signals = data.get("key_signals_identified", [])
    signals_text = "\n".join([
        f"[{signal.get('signal_type', 'other').replace('_', ' ').title()}] {signal.get('description', '')}"
        for signal in signals
    ]) if signals else "No specific signals extracted"

    # === 4. DECISION LOGIC ===
    decision = data.get("decision_logic", {})
    decision_summary = decision.get("summary", "")
    key_factors = decision.get("key_factors", [])
    decision_text = f"{decision_summary}\n\nKey Factors:\n" + "\n".join([
        f"• {factor}" for factor in key_factors
    ])

    # === 5. SYSTEM NEXT ACTION ===
    system_action = data.get("system_next_action", {})
    system_action_text = f"{system_action.get('action', '')}\n\nRationale: {system_action.get('rationale', '')}"

    # === 6. HANDLER NEXT ACTION ===
    handler_action = data.get("handler_next_action", {})
    handler_action_text = f"[{handler_action.get('priority', 'Standard').upper()}] {handler_action.get('action', '')}"

    # === 7. CONFIDENCE SCORE ===
    confidence_data = data.get("confidence", {})
    confidence_score = confidence_data.get("score", 0)
    confidence_explanation = confidence_data.get("explanation", "")
    conf_factors = confidence_data.get("factors_affecting", [])
    confidence_text = f"{confidence_score}% — {confidence_explanation}\n\nFactors:\n" + "\n".join([
        f"• {factor}" for factor in conf_factors
    ])

    # === 8. HANDLERS ===
    handlers = data.get("handlers", {})
    primary = handlers.get("primary", {})
    secondary = handlers.get("secondary")

    handler_summary = f"PRIMARY: {primary.get('name', '')} ({primary.get('handler_id', '')})\n"
    handler_summary += f"Email: {primary.get('contact_email', '')} | Phone: {primary.get('contact_phone', '')}\n"
    handler_summary += f"Reason: {primary.get('match_reason', '')}"

    if secondary:
        handler_summary += f"\n\nSECONDARY: {secondary.get('name', '')} ({secondary.get('handler_id', '')})\n"
        handler_summary += f"Email: {secondary.get('contact_email', '')} | Phone: {secondary.get('contact_phone', '')}\n"
        handler_summary += f"Reason: {secondary.get('match_reason', '')}"

    # === 9. DATA GAPS ===
    data_gaps = data.get("data_gaps", [])
    if data_gaps:
        gaps_text = "\n".join([
            f"[{gap.get('importance', 'MEDIUM').upper()}] {gap.get('field', 'Unknown')}: {gap.get('prompt', '')}"
            for gap in data_gaps
        ])
    else:
        gaps_text = "✓ All key information detected"

    # === 10. LANGUAGE DETECTION ===
    detected_lang = data.get("detected_language", {})
    lang_display = f"{detected_lang.get('name', 'Unknown')} ({detected_lang.get('code', 'N/A')}) — {detected_lang.get('confidence', 0)}% confidence"

    return (
        json_str,
        claim_type,
        severity_display,
        drivers_text,
        signals_text,
        decision_text,
        system_action_text,
        handler_action_text,
        handler_summary,
        gaps_text,
        confidence_text,
        lang_display,
    )


with gr.Blocks(css=CSS, title="Claimsprint — FNOL Triage") as demo:
    with gr.Column(elem_classes="fnol-shell"):

        # ── Hero ──────────────────────────────────────────────
        with gr.Row(elem_classes="hero"):
            with gr.Column(scale=4, elem_classes="hero-left"):
                gr.Markdown(
                    "Claimsprint — FNOL Triage",
                    elem_classes="hero-title",
                )
                gr.Markdown(
                    "Accepts a loss notification as free text, structured form input, or uploaded "
                    "document text, then returns a structured triage card with explanation-rich outputs.",
                    elem_classes="hero-subtitle",
                )
            with gr.Column(scale=1, min_width=120):
                gr.HTML(
                    '<div class="hero-badge">Live demo ready</div>'
                )

        # ── Main two-column layout ─────────────────────────────
        with gr.Row(equal_height=False):

            # Left: input panel
            with gr.Column(scale=5, elem_classes="panel"):
                example_index = gr.State(value=0)

                with gr.Tabs():
                    with gr.Tab("Free text"):
                        free_text = gr.Textbox(
                            label="Loss notification",
                            lines=12,
                            placeholder="Paste the FNOL notification text here...",
                        )

                    with gr.Tab("Structured Form"):
                        gr.Markdown("### 📋 Policy & Insured Information", elem_classes="label")
                        with gr.Row():
                            policy_number = gr.Textbox(
                                label="Policy Number *",
                                placeholder="e.g., NAC-2024-001234",
                                info="Required field"
                            )
                            insured_name = gr.Textbox(
                                label="Insured Name *",
                                placeholder="Company or individual name",
                                info="Required field"
                            )

                        gr.Markdown("### 📅 Loss Details", elem_classes="label")
                        with gr.Row():
                            date_of_loss = gr.Textbox(
                                label="Date of Loss *",
                                placeholder="YYYY-MM-DD (e.g., 2026-04-10)",
                                info="Required field - must not be in future"
                            )
                            time_of_loss = gr.Dropdown(
                                label="Time of Loss *",
                                choices=["Unknown"] + [f"{h:02d}:00" for h in range(24)] + [f"{h:02d}:30" for h in range(24)],
                                value="Unknown",
                                info="Select time or Unknown"
                            )

                        gr.Markdown("### 📍 Location of Loss", elem_classes="label")
                        with gr.Row():
                            country = gr.Dropdown(
                                label="Country *",
                                choices=[""] + [code for code, _ in COUNTRY_CHOICES],
                                info="Required field"
                            )
                            city = gr.Textbox(
                                label="City *",
                                placeholder="e.g., Hamburg, Rotterdam, Madrid",
                                info="Required field"
                            )
                        address = gr.Textbox(
                            label="Address (optional but recommended)",
                            placeholder="Street address, warehouse name, or specific location"
                        )

                        gr.Markdown("### 🏷️ Insurance Product & Incident", elem_classes="label")
                        product_type = gr.Dropdown(
                            label="Insurance Product (optional - AI will detect if left blank)",
                            choices=["Unknown / Let AI Detect"] + PRODUCT_CHOICES,
                            value="Unknown / Let AI Detect",
                            info="Select if known, otherwise AI will classify"
                        )
                        incident_type = gr.Dropdown(
                            label="Type of Incident *",
                            choices=[""] + INCIDENT_TYPE_CHOICES,
                            info="Required field - select most applicable type"
                        )

                        gr.Markdown("### 📝 Loss Description", elem_classes="label")
                        loss_description = gr.Textbox(
                            label="Description of Damage / Incident *",
                            lines=5,
                            placeholder="Describe what happened, what is damaged, and who is involved. Minimum 50 characters required.\n\nExample: Fire started in electrical panel at 02:30, spread to warehouse section B. Affected 200 pallets of electronics. Fire brigade contained damage within 2 hours. Estimated water and smoke damage to adjacent inventory.",
                            info="Required field - minimum 50 characters"
                        )

                        gr.Markdown("### 💰 Financial Impact", elem_classes="label")
                        with gr.Row():
                            estimated_value = gr.Number(
                                label="Estimated Loss Value *",
                                minimum=0,
                                info="Required field - must be greater than 0"
                            )
                            currency = gr.Dropdown(
                                label="Currency *",
                                choices=CURRENCY_CHOICES,
                                value="EUR",
                                info="Select currency"
                            )

                        # Conditional fields (with info text)
                        gr.Markdown("### 🚗 Additional Details (if applicable)", elem_classes="label")
                        gr.Markdown("**Motor Claims:** Provide vehicle details", elem_classes="small-note")
                        with gr.Row():
                            vehicle_plate = gr.Textbox(
                                label="Vehicle Plate Number",
                                placeholder="e.g., ABC-123"
                            )
                            vehicle_model = gr.Textbox(
                                label="Vehicle Model",
                                placeholder="e.g., Toyota Corolla 2023"
                            )
                            driver_name = gr.Textbox(
                                label="Driver Name",
                                placeholder="Full name of driver"
                            )

                        gr.Markdown("**Property Claims:** Property and damage details", elem_classes="small-note")
                        with gr.Row():
                            property_type = gr.Dropdown(
                                label="Property Type",
                                choices=["", "Commercial Building", "Warehouse", "Factory", "Office", "Residential", "Construction Site", "Other"],
                            )
                            damage_type = gr.Dropdown(
                                label="Damage Type",
                                choices=["", "Structural Damage", "Contents Only", "Both Structural and Contents", "Total Loss"],
                            )

                        gr.Markdown("**Health/Personal Accident Claims:** Medical details", elem_classes="small-note")
                        with gr.Row():
                            hospital_name = gr.Textbox(
                                label="Hospital/Clinic Name",
                                placeholder="Medical facility name"
                            )
                            treatment_type = gr.Textbox(
                                label="Treatment Type",
                                placeholder="e.g., Surgery, Hospitalization, Outpatient"
                            )

                        gr.Markdown("**Marine Cargo Claims:** Shipping details", elem_classes="small-note")
                        with gr.Row():
                            vessel_name = gr.Textbox(
                                label="Vessel/Container Name",
                                placeholder="Vessel or container ID"
                            )
                            bill_of_lading = gr.Textbox(
                                label="Bill of Lading / CMR Reference",
                                placeholder="B/L or CMR number"
                            )

                    with gr.Tab("Upload"):
                                doc_file = gr.File(
                                    file_types=[".txt", ".md", ".json", ".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".tif", ".tiff"],
                                    label="Upload Extracted Document Text",
                                )
                                gr.Markdown(
                                    "Upload text, PDF, DOCX, or image files. PDF/image text is extracted via Textract.",
                                    elem_classes="small-note",
                                )

                with gr.Row():
                    run_btn = gr.Button("Run triage", elem_classes="run-btn")
                    clear_btn = gr.ClearButton(
                        [
                            free_text, doc_file,
                            policy_number, insured_name, date_of_loss, time_of_loss,
                            country, city, address, product_type, incident_type,
                            loss_description, estimated_value, currency,
                            vehicle_plate, vehicle_model, driver_name,
                            property_type, damage_type,
                            hospital_name, treatment_type,
                            vessel_name, bill_of_lading,
                        ],
                        value="Clear All",
                        elem_classes="ghost-btn",
                    )

            # Right: output panel
            with gr.Column(scale=4, elem_classes="panel"):
                gr.Markdown("Business-Aligned Triage Card", elem_classes="label")

                # === PRIORITY 1: Claim Type ===
                claim_type_out = gr.Textbox(
                    label="Claim Type",
                    interactive=False,
                    elem_classes="card",
                    lines=1,
                )

                # === PRIORITY 2: Severity (with drivers) ===
                with gr.Row():
                    severity_out = gr.Textbox(
                        label="Severity",
                        interactive=False,
                        elem_classes="card",
                        lines=1,
                    )
                    confidence_out = gr.Textbox(
                        label="Confidence Score",
                        interactive=False,
                        elem_classes="card",
                        lines=3,
                    )

                severity_drivers_out = gr.Textbox(
                    label="Severity Drivers (Why this severity?)",
                    lines=4,
                    interactive=False,
                    elem_classes="card",
                )

                # === PRIORITY 3: Recommended Next Actions ===
                system_action_out = gr.Textbox(
                    label="Recommended Next Action (System-Level)",
                    lines=3,
                    interactive=False,
                    elem_classes="card",
                )

                handler_action_out = gr.Textbox(
                    label="Handler Recommendation (User-Level)",
                    lines=2,
                    interactive=False,
                    elem_classes="card",
                )

                # === PRIORITY 4: Handler Assignment ===
                handler_out = gr.Textbox(
                    label="Assigned Handler",
                    lines=4,
                    interactive=False,
                    elem_classes="card",
                )

                # === PRIORITY 5: Supporting Evidence ===
                signals_out = gr.Textbox(
                    label="Key Signals Identified",
                    lines=4,
                    interactive=False,
                    elem_classes="card",
                )

                decision_logic_out = gr.Textbox(
                    label="Decision Summary",
                    lines=4,
                    interactive=False,
                    elem_classes="card",
                )

                # === PRIORITY 6: Data Quality ===
                gaps_out = gr.Textbox(
                    label="What We Still Need",
                    lines=4,
                    interactive=False,
                    elem_classes="card",
                )

                # Language detection
                lang_out = gr.Textbox(
                    label="Detected Language",
                    interactive=False,
                    elem_classes="card",
                    lines=1,
                )

                json_out = gr.Textbox(
                    label="Structured JSON Output",
                    lines=10,
                    interactive=False,
                    elem_classes="panel-soft",
                )

        # ── Wire up events ─────────────────────────────────────
        run_btn.click(
            triage_and_parse,
            inputs=[
                # Free text / Upload (legacy)
                free_text,
                doc_file,
                # New structured form fields (in order of function signature)
                policy_number, insured_name, date_of_loss, time_of_loss,
                country, city, address, product_type, incident_type,
                loss_description, estimated_value, currency,
                # Conditional fields
                vehicle_plate, vehicle_model, driver_name,
                property_type, damage_type,
                hospital_name, treatment_type,
                vessel_name, bill_of_lading,
            ],
            outputs=[
                json_out,
                claim_type_out,
                severity_out,
                severity_drivers_out,
                signals_out,
                decision_logic_out,
                system_action_out,
                handler_action_out,
                handler_out,
                gaps_out,
                confidence_out,
                lang_out,
            ],
        )

        EXAMPLES = [
            (
                "Received notification from warehouse operator DHL Supply Chain Germany at 14:15 CET. "
                "Fire alarm triggered overnight at a bonded warehouse in Hamburg. Preliminary report indicates "
                "an electrical fault in a storage rack caused a localized fire, which spread to adjacent pallets "
                "before being contained by the sprinkler system. Affected goods include consumer electronics "
                "(laptops and tablets) belonging to multiple consignees, with an estimated total value of EUR 1.8 million. "
                "Fire brigade report and initial incident photos attached. Insured party (TechDistrib GmbH) "
                "reports partial and total losses across several shipments and is requesting urgent surveyor appointment."
            ),
            (
                "Rotterdam cold-chain cargo loss reported. Refrigerated pharma shipment experienced a "
                "temperature breach after reefer power failure at the terminal. Estimated loss EUR 620,000. "
                "Temperature logs and terminal incident report available. Urgent guidance requested to salvage stock."
            ),
            (
                "Liability injury in Kuala Lumpur warehouse. Third-party contractor slipped on wet floor and "
                "sustained a leg fracture. Claimant has retained counsel and requested medical expense reimbursement. "
                "Incident report filed, CCTV available. Estimated exposure USD 180,000."
            ),
            (
                "Marine cargo loss reported by freight forwarder Expeditors International. Container vessel MV Stellanova "
                "encountered heavy weather in the Bay of Biscay. Three containers of automotive parts shifted and sustained "
                "water ingress damage. Insured: AutoPartsEU GmbH. Estimated value EUR 340,000. Bill of lading and "
                "packing lists attached. Surveyor access requested at Port of Bilbao upon arrival."
            ),
            (
                "Construction all-risk claim submitted. Partial collapse of scaffolding at a commercial build site in "
                "Manchester during high winds. No injuries reported. Structural damage to facade and internal fit-out. "
                "Project insured: Meridian Construction Ltd. Estimated remediation cost GBP 890,000. Engineer's "
                "preliminary assessment attached. Works suspended pending inspection."
            ),
        ]

demo.launch(debug=False, share=False, server_name="0.0.0.0", server_port=7860)
