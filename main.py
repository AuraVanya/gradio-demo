import gradio as gr
from motor_quote import process_image
from acord_extractor import process_pdf

# --- Gradio Functions --- #

# Create custom theme with gray buttons
custom_theme = gr.themes.Default(
    primary_hue="slate",
    secondary_hue="slate",
)

# ACORD Form Extractor Gradio Interface
acord_extractor = gr.Interface(
    fn=process_pdf,
    inputs=gr.File(file_types=[".pdf"], label="Upload ACORD 125 Form"),
    outputs=[
        gr.Textbox(label="Bedrock JSON Output", lines=20),
        gr.Dataframe(
            label="Textract Extracted Data with Confidence Scores",
            column_widths=["40%", "30%", "15%", "15%"],
            wrap=True
        )
    ],
    description="Upload an ACORD 125 Form, it will be sent to S3, processed by Textract, and interpreted by Bedrock LLM.",
    flagging_mode='never'
)

# Motor Quote Image Analysis Gradio Interface
motor_quote = gr.Interface(
    fn=process_image,
    inputs= gr.File(file_types=[".png", ".jpg", ".jpeg"], label="Upload Vehicle Image"),
    outputs=[
        gr.Textbox(label="Rekognition JSON Output", lines=20),
        gr.Dataframe(label="Rekognition Image Analysis with Confidence Scores", wrap=True)
    ],
    description="Upload an image to analyze it with AWS Rekognition. Detects labels, text, faces, and content moderation.",
    flagging_mode='never'
)

demo = gr.TabbedInterface([
    acord_extractor,
    motor_quote,
    ],
    [
    "ACORD Extractor",
    "Motor Quote",
    ],
    theme=custom_theme
)

demo.launch(debug=True)
