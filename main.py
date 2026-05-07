# main.py (updated)
import shutil
import tempfile
import copy
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from docling.datamodel import asr_model_specs
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import AsrPipelineOptions, PdfPipelineOptions
from docling.document_converter import (
    AudioFormatOption,
    DocumentConverter,
    PdfFormatOption,
)
from docling.pipeline.asr_pipeline import AsrPipeline

app = FastAPI(title="Docling Multi-Format API")

AUDIO_VIDEO_FORMATS = {".mp3", ".wav", ".mp4", ".mov", ".avi", ".m4a", ".ogg"}
IMAGE_FORMATS       = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
PDF_FORMATS         = {".pdf"}


# --- ASR converter (audio/video) ---
def build_asr_converter(language: str = "en") -> DocumentConverter:
    asr_opts = copy.deepcopy(asr_model_specs.WHISPER_TURBO)
    asr_opts.language = language
    pipeline_options = AsrPipelineOptions()
    pipeline_options.asr_options = asr_opts
    return DocumentConverter(
        format_options={
            InputFormat.AUDIO: AudioFormatOption(
                pipeline_cls=AsrPipeline,
                pipeline_options=pipeline_options,
            )
        }
    )


# --- PDF converter ---
def build_pdf_converter(do_ocr: bool = True) -> DocumentConverter:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = do_ocr                  # OCR for scanned PDFs
    pipeline_options.do_table_structure = True         # Extract tables
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            )
        }
    )


# --- Image converter (OCR) ---
def build_image_converter() -> DocumentConverter:
    return DocumentConverter()


# Load all three converters once at startup
asr_converter   = build_asr_converter()
pdf_converter   = build_pdf_converter()
image_converter = build_image_converter()


@app.post("/convert")
async def convert(
    file: UploadFile = File(...),
    output_format: str = "markdown",
    language: str = "en",          # ASR only
    do_ocr: bool = True,           # PDF only — set False for text-native PDFs
):
    suffix = Path(file.filename).suffix.lower()

    if suffix in AUDIO_VIDEO_FORMATS:
        converter = asr_converter
        pipeline  = "asr"
    elif suffix in PDF_FORMATS:
        # Rebuild if do_ocr differs from default, else reuse cached
        converter = build_pdf_converter(do_ocr=do_ocr)
        pipeline  = "pdf"
    elif suffix in IMAGE_FORMATS:
        converter = image_converter
        pipeline  = "ocr"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported type '{suffix}'. Supported: "
                   f"{AUDIO_VIDEO_FORMATS | PDF_FORMATS | IMAGE_FORMATS}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = converter.convert(tmp_path)
        doc    = result.document

        if output_format == "json":
            content = doc.export_to_dict()
        elif output_format == "html":
            content = doc.export_to_html()
        else:
            content = doc.export_to_markdown()

        return JSONResponse({
            "filename": file.filename,
            "pipeline": pipeline,
            "format":   output_format,
            "content":  content,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}