from docling.datamodel import asr_model_specs
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import AsrPipelineOptions, PdfPipelineOptions
from docling.document_converter import (
    AudioFormatOption,
    DocumentConverter,
    PdfFormatOption,
)
from docling.pipeline.asr_pipeline import AsrPipeline
import copy


# ASR converter (audio/video)
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


# PDF converter
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


# Image converter (OCR)
def build_image_converter() -> DocumentConverter:
    return DocumentConverter()