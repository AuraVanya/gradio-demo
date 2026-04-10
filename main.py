import json
import gradio as gr
from functions.fnol_triage import triage_fnol

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root {
  --ink: #0f172a;
  --muted: #64748b;
  --panel: #ffffff;
  --panel-soft: #f8fafc;
  --line: #e2e8f0;
  --accent: #0f172a;
  --accent-soft: #0f172a10;
  --bg: #f2f5f9;
  --bg-2: #e8eef6;
}

body, .gradio-container {
  font-family: "Plus Jakarta Sans", system-ui, -apple-system, sans-serif;
  background: radial-gradient(1200px 400px at 10% -10%, var(--bg-2), transparent),
              radial-gradient(900px 360px at 90% -20%, #e9eef7, transparent),
              var(--bg);
  color: var(--ink);
}

.fnol-shell {
  max-width: 1200px;
  margin: 0 auto;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 12px 0 4px 0;
}

.hero-title {
  font-family: "Space Grotesk", "Plus Jakarta Sans", sans-serif;
  font-size: 34px;
  font-weight: 700;
  margin-bottom: 6px;
}

.hero-title p {
  margin: 0;
}

.hero-subtitle {
  color: var(--muted);
  font-size: 15px;
  line-height: 1.5;
  max-width: 520px;
}

.hero-subtitle p {
  margin: 0;
}

.label {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  margin-bottom: 8px;
}

.hero-badge {
  background: var(--ink);
  color: #fff;
  padding: 10px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 18px 40px -30px rgba(15, 23, 42, 0.35);
}

.panel-soft {
  background: var(--panel-soft);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
}

.card {
  background: var(--panel-soft);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
}

.card label {
  color: var(--muted) !important;
  font-size: 12px !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600 !important;
}

.card textarea,
.card input {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  font-weight: 600;
  font-size: 14px;
}

.chip-row button {
  border-radius: 999px !important;
  border: 1px solid var(--line) !important;
  background: #fff !important;
  font-weight: 600 !important;
}

.run-btn button {
  background: var(--ink) !important;
  color: #fff !important;
  border-radius: 999px !important;
  font-weight: 600 !important;
  padding: 10px 18px !important;
}

.ghost-btn button {
  border-radius: 999px !important;
  font-weight: 600 !important;
}

.gradio-container .tabs > .tab-nav button {
  font-weight: 600;
}

.small-note {
  color: var(--muted);
  font-size: 12px;
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
        return json_str, "", "", "", "", "", "", ""

    severity_factors = data.get("severity_factors", [])
    severity_factors_text = "\n".join([f"• {item}" for item in severity_factors])
    handler = data.get("recommended_handler", {}) or {}
    handler_summary = " ".join(
        part for part in [
            f"{handler.get('name', '')}",
            f"— {handler.get('role', '')}" if handler.get("role") else "",
            f"({handler.get('region', '')}, {handler.get('speciality', '')})"
            if handler.get("region") or handler.get("speciality") else "",
        ] if part
    ).strip()
    if handler.get("reason"):
        handler_summary = f"{handler_summary}\n{handler.get('reason')}".strip()

    return (
        json_str,
        data.get("claim_type", ""),
        data.get("claim_subtype", ""),
        data.get("severity", ""),
        data.get("recommended_action", ""),
        severity_factors_text,
        data.get("action_reasoning", ""),
        handler_summary,
    )


with gr.Blocks(css=CSS, title="Claimsprint — FNOL Triage Prototype") as demo:
    with gr.Column(elem_classes="fnol-shell"):
                with gr.Row(elem_classes="hero"):
                    with gr.Column(scale=3):
                        gr.Markdown(
                            "Claimsprint — FNOL Triage Prototype",
                            elem_classes="hero-title",
                        )
                        gr.Markdown(
                            "Accepts a loss notification as free text, structured form input, or uploaded "
                            "document text, then returns a structured triage card with explanation-rich outputs "
                            "for a live judge demo.",
                            elem_classes="hero-subtitle",
                        )
                    with gr.Column(scale=1, min_width=140):
                        gr.Markdown("Live demo ready", elem_classes="hero-badge")

                with gr.Row():
                    with gr.Column(scale=5, elem_classes="panel"):
                        gr.Markdown("Quick examples", elem_classes="label")
                        with gr.Row(elem_classes="chip-row"):
                            sample_fire = gr.Button("Hamburg warehouse fire")
                            sample_temp = gr.Button("Rotterdam cold-chain loss")
                            sample_liability = gr.Button("Kuala Lumpur injury claim")

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
                                    file_types=[".txt", ".md", ".json", ".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"],
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
                                value="Clear inputs",
                                elem_classes="ghost-btn",
                            )

                    with gr.Column(scale=4, elem_classes="panel"):
                        gr.Markdown("Structured triage card", elem_classes="label")
                        with gr.Row():
                            claim_type_out = gr.Textbox(
                                label="Claim type",
                                interactive=False,
                                elem_classes="card",
                            )
                            claim_subtype_out = gr.Textbox(
                                label="Claim subtype",
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
                        json_out = gr.Textbox(
                            label="Structured JSON output",
                            lines=12,
                            interactive=False,
                            elem_classes="panel-soft",
                        )

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
                    ],
                )

                sample_fire.click(
                    lambda: (
                        "Received notification from warehouse operator DHL Supply Chain Germany at 14:15 CET. "
                        "Fire alarm triggered overnight at a bonded warehouse in Hamburg. Preliminary report indicates "
                        "an electrical fault in a storage rack caused a localized fire, which spread to adjacent pallets "
                        "before being contained by the sprinkler system. Affected goods include consumer electronics "
                        "(laptops and tablets) belonging to multiple consignees, with an estimated total value of EUR 1.8 million. "
                        "Fire brigade report and initial incident photos attached. Insured party (TechDistrib GmbH) "
                        "reports partial and total losses across several shipments and is requesting urgent surveyor appointment."
                    ),
                    inputs=[],
                    outputs=[free_text],
                )
                sample_temp.click(
                    lambda: (
                        "Rotterdam cold-chain cargo loss reported. Refrigerated pharma shipment experienced a "
                        "temperature breach after reefer power failure at the terminal. Estimated loss EUR 620,000. "
                        "Temperature logs and terminal incident report available. Urgent guidance requested to salvage stock."
                    ),
                    inputs=[],
                    outputs=[free_text],
                )
                sample_liability.click(
                    lambda: (
                        "Liability injury in Kuala Lumpur warehouse. Third-party contractor slipped on wet floor and "
                        "sustained a leg fracture. Claimant has retained counsel and requested medical expense reimbursement. "
                        "Incident report filed, CCTV available. Estimated exposure USD 180,000."
                    ),
                    inputs=[],
                    outputs=[free_text],
                )

demo.launch(debug=False, share=False, server_name="0.0.0.0", server_port=7860)
