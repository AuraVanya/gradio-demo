import gradio as gr
from functions.motor_quote import process_images
from functions.acord_extractor import process_pdf

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
            column_widths=["30%", "30%", "20%", "20%"],
            wrap=True
        )
    ],
    description="Upload an ACORD 125 Form, it will be sent to S3, processed by Textract, and interpreted by Bedrock LLM.",
    flagging_mode='never'
)

# Motor Quote Image Analysis Gradio Interface
motor_quote = gr.Interface(
    fn=process_images,
    inputs=[
        gr.File(file_types=[".png", ".jpg", ".jpeg"], label="Upload Vehicle Image"),
        gr.File(file_types=[".png", ".jpg", ".jpeg"], label="Upload Driver's License Image")
    ],
    outputs=[
        gr.Dataframe(
            label="Vehicle Analysis (AWS Rekognition)",
             column_widths=["20%", "20%", "35%", "15%"],
            wrap=True),
        gr.Dataframe(
            label="Driver's License Extraction (AWS Textract)",
            column_widths=["20%", "40%", "15%", "15%"],
            wrap=True)
        ],
    description="Upload a vehicle image and a driver's license image. The vehicle will be analyzed with AWS Rekognition, and the license will be processed with AWS Textract to extract key-value pairs.",
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
