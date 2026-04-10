import gradio as gr
from functions.visual_analysis import process_images
from functions.acord_extractor import process_pdf

# --- Gradio Functions --- #

# # Create custom theme with gray buttons
# custom_theme = gr.themes.Default(
#     primary_hue="slate",
#     secondary_hue="slate",
# )

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
    description="Upload an ACORD 125 Form. The form will be sent to S3, processed by AWS Textract, and Bedrock will structure the data into a standard JSON format.",
    # allow_flagging='never'
)

# Motor Quote Image Analysis Gradio Interface
motor_quote = gr.Interface(
    fn=process_images,
    inputs=[
        gr.File(file_types=[".png", ".jpg", ".jpeg"], label="Upload Vehicle Image"),
        gr.File(file_types=[".png", ".jpg", ".jpeg"], label="Upload Driver's License Image")
    ],
    outputs=[
        gr.Textbox(
            label="Bedrock JSON Output",
            lines=20),
        gr.Dataframe(
            label="Vehicle Visual Analysis with Confidence Scores",
            column_widths=["20%", "20%", "35%", "15%"],
            wrap=True),
        gr.Dataframe(
            label="Driver License Visual Analysis with Confidence Scores",
            column_widths=["20%", "40%", "15%", "15%"],
            wrap=True)
    ],
    description="Upload a vehicle image and a driver's license image. The images will be sent to S3, processed by AWS Rekognition, and Bedrock will structure the data into a standard JSON format.",
    # allow_flagging='never'
)

# Combine both interfaces into a tabbed layout
demo = gr.TabbedInterface([
    acord_extractor,
    motor_quote,
    ],
    [
    "ACORD Extractor",
    "Vehicle Visual Analysis",
    ],
    # theme=custom_theme
)

demo.launch(debug=False, share=False, server_name="0.0.0.0", server_port=7860)
