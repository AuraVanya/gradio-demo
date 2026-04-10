import json
import gradio as gr
from functions.fnol_triage import triage_fnol

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


def triage_and_parse(
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
    json_str = triage_fnol(
        free_text,
        doc_file,
        insured_name,
        policy_number,
        location,
        estimated_value,
        urgency_notes,
        documents_list,
        extra_notes,
    )

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return json_str, "", "", "", "", "", "", "", "Error parsing JSON", "Unknown"

    # Extract classification
    classification = data.get("classification", {})
    claim_type = f"{classification.get('lob_display_name', '')} ({classification.get('lob_code', '')})"

    # Extract insurance product (replaces claim_subtype)
    insurance_product = classification.get("insurance_product", "")

    # Extract severity with score
    severity_data = data.get("severity", {})
    severity_level = severity_data.get("level", "")
    severity_score = severity_data.get("score", 0)
    severity_display = f"{severity_level} ({severity_score}/100)"

    # Extract severity factors with weights
    severity_factors = severity_data.get("factors", [])
    severity_factors_text = "\n".join([
        f"[{item.get('weight', '').upper()}] {item.get('text', '')}"
        for item in severity_factors
    ])

    # Extract recommended action
    action_data = data.get("recommended_action", {})
    action_label = action_data.get("label", "")
    action_reasoning = action_data.get("reasoning", "")

    # Extract steps as formatted list
    steps = action_data.get("steps", [])
    steps_text = "\n".join([f"• {step}" for step in steps]) if steps else ""
    action_full = f"{action_reasoning}\n\nNext Steps:\n{steps_text}" if steps else action_reasoning

    # Extract handler information with full details
    handlers = data.get("handlers", {})
    primary = handlers.get("primary", {})
    secondary = handlers.get("secondary")

    handler_summary = f"PRIMARY: {primary.get('name', '')} ({primary.get('handler_id', '')})\n"
    handler_summary += f"Role: {primary.get('role', '')}\n"
    handler_summary += f"Email: {primary.get('email', '')} | Phone: {primary.get('phone', '')}\n"
    handler_summary += f"Reason: {primary.get('match_reason', '')}"

    if secondary:
        handler_summary += f"\n\nSECONDARY: {secondary.get('name', '')} ({secondary.get('handler_id', '')})\n"
        handler_summary += f"Role: {secondary.get('role', '')}\n"
        handler_summary += f"Email: {secondary.get('email', '')} | Phone: {secondary.get('phone', '')}\n"
        handler_summary += f"Reason: {secondary.get('match_reason', '')}"

    # Extract data gaps for "What We Still Need" panel
    data_gaps = data.get("data_gaps", [])
    if data_gaps:
        gaps_text = "\n".join([
            f"• {gap.get('field', 'Unknown')}: {gap.get('prompt', 'Please provide this information')}"
            for gap in data_gaps
        ])
    else:
        gaps_text = "✓ All key information detected"

    # Extract language detection
    detected_lang = data.get("detected_language", {})
    lang_display = f"{detected_lang.get('name', 'Unknown')} ({detected_lang.get('code', 'N/A')}) - {detected_lang.get('confidence', 0)}% confidence"

    return (
        json_str,
        claim_type,
        insurance_product,
        severity_display,
        action_label,
        severity_factors_text,
        action_full,
        handler_summary,
        gaps_text,
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

                    with gr.Tab("Form input"):
                        insured_name = gr.Textbox(label="Insured Name (optional)")
                        policy_number = gr.Textbox(label="Policy Number (optional)")
                        location = gr.Textbox(label="Loss Location (optional)")
                        estimated_value = gr.Textbox(label="Estimated Value (optional)")
                        urgency_notes = gr.Textbox(label="Urgency Notes (optional)")
                        documents_list = gr.Textbox(label="Documents Available (optional)")
                        extra_notes = gr.Textbox(label="Additional Notes (optional)", lines=3)
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
                            free_text,
                            insured_name,
                            policy_number,
                            location,
                            estimated_value,
                            urgency_notes,
                            documents_list,
                            extra_notes,
                            doc_file,
                        ],
                        value="Clear",
                        elem_classes="ghost-btn",
                    )

            # Right: output panel
            with gr.Column(scale=4, elem_classes="panel"):
                gr.Markdown("Structured triage card", elem_classes="label")

                # Language detection banner
                lang_out = gr.Textbox(
                    label="Detected Language",
                    interactive=False,
                    elem_classes="card",
                    lines=1,
                )

                with gr.Row():
                    claim_type_out = gr.Textbox(
                        label="Claim type",
                        interactive=False,
                        elem_classes="card",
                    )
                    claim_subtype_out = gr.Textbox(
                        label="Insurance Product",
                        interactive=False,
                        elem_classes="card",
                    )
                with gr.Row():
                    severity_out = gr.Textbox(
                        label="Severity",
                        interactive=False,
                        elem_classes="card",
                    )
                    action_out = gr.Textbox(
                        label="Recommended action",
                        interactive=False,
                        elem_classes="card",
                    )
                severity_factors_out = gr.Textbox(
                    label="Severity factors",
                    lines=6,
                    interactive=False,
                    elem_classes="card",
                )
                action_reasoning_out = gr.Textbox(
                    label="Action reasoning",
                    lines=5,
                    interactive=False,
                    elem_classes="card",
                )
                handler_out = gr.Textbox(
                    label="Recommended handler",
                    lines=4,
                    interactive=False,
                    elem_classes="card",
                )

                # What We Still Need panel (REQ-08)
                gaps_out = gr.Textbox(
                    label="What We Still Need",
                    lines=4,
                    interactive=False,
                    elem_classes="card",
                )

                json_out = gr.Textbox(
                    label="Structured JSON output",
                    lines=12,
                    interactive=False,
                    elem_classes="panel-soft",
                )

        # ── Wire up events ─────────────────────────────────────
        run_btn.click(
            triage_and_parse,
            inputs=[
                free_text,
                doc_file,
                insured_name,
                policy_number,
                location,
                estimated_value,
                urgency_notes,
                documents_list,
                extra_notes,
            ],
            outputs=[
                json_out,
                claim_type_out,
                claim_subtype_out,
                severity_out,
                action_out,
                severity_factors_out,
                action_reasoning_out,
                handler_out,
                gaps_out,
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
