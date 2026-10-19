"""
PDF Operations: 100% offline merging, page extraction, compression, and splitting.
"""
from pathlib import Path
from typing import Optional
import pypdf
import pypdfium2 as pdfium

def merge_pdfs(
    pdf_paths: list[Path | str],
    output_path: Optional[Path | str] = None
) -> Path:
    """
    Merges multiple PDF files in order into a single PDF.
    """
    if not pdf_paths:
        raise ValueError("No se proporcionaron archivos PDF para combinar.")

    first_pdf = Path(pdf_paths[0])
    target = Path(output_path) if output_path else first_pdf.parent / f"{first_pdf.stem}_merged.pdf"

    writer = pypdf.PdfWriter()
    for p in pdf_paths:
        reader = pypdf.PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)

    with open(target, "wb") as f:
        writer.write(f)

    return target


def pdf_to_images(
    input_path: Path | str,
    output_format: str = "png",
    dpi: int = 200,
    output_dir: Optional[Path | str] = None
) -> list[Path]:
    """
    Converts all pages of a PDF to high-resolution images.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent / f"{input_path.stem}_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf = pdfium.PdfDocument(str(input_path))
    output_files = []

    # Render scale from DPI (72 dpi is scale 1.0)
    scale = dpi / 72.0

    for i, page in enumerate(pdf):
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        target_file = out_dir / f"page_{i+1:03d}.{output_format}"
        pil_image.save(target_file)
        output_files.append(target_file)

    return output_files


def compress_pdf(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Compresses PDF streams and removes duplicate objects.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target = out_dir / f"{input_path.stem}_min.pdf"

    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()

    for page in reader.pages:
        page.compress_content_streams()  # Flate compression
        writer.add_page(page)

    writer.add_metadata(reader.metadata or {})
    with open(target, "wb") as f:
        writer.write(f)

    return target


def split_pdf(
    input_path: Path | str,
    pages_per_split: int = 1,
    output_dir: Optional[Path | str] = None
) -> list[Path]:
    """
    Splits a PDF into individual pages or batches of N pages.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent / f"{input_path.stem}_split"
    out_dir.mkdir(parents=True, exist_ok=True)

    reader = pypdf.PdfReader(str(input_path))
    total_pages = len(reader.pages)
    output_files = []

    for i in range(0, total_pages, pages_per_split):
        writer = pypdf.PdfWriter()
        chunk_pages = reader.pages[i : i + pages_per_split]
        for p in chunk_pages:
            writer.add_page(p)

        end_page = min(i + pages_per_split, total_pages)
        part_name = f"pages_{i+1:03d}-{end_page:03d}.pdf" if pages_per_split > 1 else f"page_{i+1:03d}.pdf"
        target_part = out_dir / part_name
        with open(target_part, "wb") as f:
            writer.write(f)
        output_files.append(target_part)

    return output_files
