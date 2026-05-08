# main.py (updated)
import shutil
import tempfile
from pathlib import Path
import time

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from docling_fxns import build_asr_converter, build_pdf_converter, build_image_converter

# Define supported formats
AUDIO_VIDEO_FORMATS = {".mp3", ".wav", ".mp4", ".mov", ".avi", ".m4a", ".ogg"}
IMAGE_FORMATS       = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
PDF_FORMATS         = {".pdf", ".docx"}


# Load all three converters once at startup
asr_converter   = build_asr_converter()
pdf_converter   = build_pdf_converter()
image_converter = build_image_converter()


app = FastAPI(title="Docling Multi-Format API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/convert")
async def convert(
    file: UploadFile = File(...),
    output_format: str = "markdown",
    language: str = "en",          # ASR only
    do_ocr: bool = True,           # PDF only — set False for text-native PDFs
):
    suffix = Path(file.filename).suffix.lower()

    # Start the timer
    start_time = time.perf_counter()

    if suffix in AUDIO_VIDEO_FORMATS:
        converter = asr_converter
        pipeline  = "asr"
        engine = "WHISPER_TURBO"  # Placeholder for future engine selection
    elif suffix in PDF_FORMATS:
        # Rebuild if do_ocr differs from default, else reuse cached
        converter = build_pdf_converter(do_ocr=do_ocr)
        pipeline  = "pdf"
        engine = "DOCLING"  # Placeholder for future engine selection
    elif suffix in IMAGE_FORMATS:
        converter = image_converter
        pipeline  = "ocr"
        engine = "WHISPER_TURBO"  # Placeholder for future engine selection
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

        end_time = time.perf_counter()
        processing_time = end_time - start_time

        return JSONResponse({
            "processing_time": processing_time,
            "title": file.filename,
            "pipeline": pipeline,
            "format":   output_format,
            "engine":   engine,
            "transcript":  content,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


async def get_converted_data():
    # Placeholder for future implementation
    return {"message": "This endpoint will return converted data."}


@app.get("/health")
def health():
    return {"status": "ok"}