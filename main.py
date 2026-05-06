# main.py
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from docling.datamodel import asr_model_specs
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import AsrPipelineOptions, PdfPipelineOptions
from docling.document_converter import AudioFormatOption, DocumentConverter
from docling.pipeline.asr_pipeline import AsrPipeline

app = FastAPI(title="Docling Transcription API")

AUDIO_VIDEO_FORMATS = {".mp3", ".wav", ".mp4", ".mov", ".avi", ".m4a", ".ogg"}
IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


# --- Converter for audio/video (ASR / Whisper) ---
def build_asr_converter() -> DocumentConverter:
    pipeline_options = AsrPipelineOptions()
    pipeline_options.asr_options = asr_model_specs.WHISPER_TURBO
    return DocumentConverter(
        format_options={
            InputFormat.AUDIO: AudioFormatOption(
                pipeline_cls=AsrPipeline,
                pipeline_options=pipeline_options,
            )
        }
    )


# --- Converter for images (OCR) ---
def build_image_converter() -> DocumentConverter:
    # Default DocumentConverter handles images via OCR out of the box
    return DocumentConverter()


# Load both converters once at startup
asr_converter = build_asr_converter()
image_converter = build_image_converter()


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), output_format: str = "markdown"):
    """
    - Audio/Video: transcribed via Whisper ASR
    - Images: text extracted via OCR
    Supported output_format: markdown, json, html
    """
    suffix = Path(file.filename).suffix.lower()

    if suffix in AUDIO_VIDEO_FORMATS:
        selected_converter = asr_converter
    elif suffix in IMAGE_FORMATS:
        selected_converter = image_converter
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. "
                   f"Supported: {AUDIO_VIDEO_FORMATS | IMAGE_FORMATS}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = selected_converter.convert(tmp_path)
        doc = result.document

        if output_format == "json":
            content = doc.export_to_dict()
        elif output_format == "html":
            content = doc.export_to_html()
        else:
            content = doc.export_to_markdown()

        return JSONResponse({
            "filename": file.filename,
            "format": output_format,
            "pipeline": "asr" if suffix in AUDIO_VIDEO_FORMATS else "ocr",
            "content": content,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)