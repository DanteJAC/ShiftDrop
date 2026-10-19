"""
Multi-File Operations: Combining, merging, and batch conversions for multiple files.
Supports combining any mix of images, PDFs, Word docs, spreadsheets, and text into a single PDF or Word document,
as well as batch conversion to target formats.
"""
import tempfile
from pathlib import Path
from typing import Optional
import pypdf
from PIL import Image

from shiftdrop.core.path_utils import get_unique_target_path
from shiftdrop.core.image_ops import convert_image
from shiftdrop.core.pdf_ops import compress_pdf, pdf_to_images
from shiftdrop.core.doc_ops import doc_to_pdf, doc_to_docx, pdf_to_docx, doc_to_txt
from shiftdrop.core.excel_ops import excel_to_pdf, excel_to_docx, excel_to_csv


def combine_files_to_pdf(
    file_paths: list[Path | str],
    output_pdf: Optional[Path | str] = None
) -> Path:
    """
    Merges any list of files (Images, PDFs, Word docs, Excel sheets, Text files)
    into a single unified, multi-page vector PDF in the exact order selected.
    Saved non-destructively in the directory of the first file.
    """
    if not file_paths:
        raise ValueError("No se proporcionaron archivos para unir en PDF.")

    paths = [Path(p).resolve() for p in file_paths]
    first_p = paths[0]
    if output_pdf:
        out_p = Path(output_pdf)
        if out_p.is_dir() or not out_p.suffix:
            target_base = out_p / f"{first_p.stem}_combinado.pdf"
        else:
            target_base = out_p
    else:
        target_base = first_p.parent / f"{first_p.stem}_combinado.pdf"
    target_pdf = get_unique_target_path(target_base)

    writer = pypdf.PdfWriter()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        for idx, p in enumerate(paths):
            if not p.exists():
                continue

            ext = p.suffix.lower()
            
            # 1. Existing PDF
            if ext == ".pdf":
                try:
                    reader = pypdf.PdfReader(str(p))
                    for page in reader.pages:
                        writer.add_page(page)
                    continue
                except Exception:
                    pass

            # 2. Image formats (.png, .jpg, .jpeg, .webp, .bmp, .tiff, etc.)
            image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".ico", ".gif"}
            if ext in image_extensions:
                try:
                    with Image.open(p) as img:
                        rgb = img.convert("RGB")
                        temp_pdf_page = tmp_path / f"img_{idx}.pdf"
                        rgb.save(temp_pdf_page, format="PDF", resolution=100.0)
                        reader = pypdf.PdfReader(str(temp_pdf_page))
                        for page in reader.pages:
                            writer.add_page(page)
                    continue
                except Exception:
                    pass

            # 3. Spreadsheets (.xlsx, .xls, .csv, .tsv)
            spreadsheet_extensions = {".xlsx", ".xls", ".xlsm", ".csv", ".tsv", ".ods"}
            if ext in spreadsheet_extensions:
                try:
                    temp_pdf_page = excel_to_pdf(p, output_dir=tmp_path)
                    reader = pypdf.PdfReader(str(temp_pdf_page))
                    for page in reader.pages:
                        writer.add_page(page)
                    continue
                except Exception:
                    pass

            # 4. Documents (.docx, .doc, .txt, .md, .rtf, .log)
            try:
                temp_pdf_page = doc_to_pdf(p, output_dir=tmp_path)
                reader = pypdf.PdfReader(str(temp_pdf_page))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception:
                pass

    if len(writer.pages) == 0:
        raise RuntimeError("No se pudo extraer ni convertir ninguna página al PDF combinado.")

    with open(target_pdf, "wb") as f:
        writer.write(f)

    return target_pdf


def combine_files_to_docx(
    file_paths: list[Path | str],
    output_docx: Optional[Path | str] = None
) -> Path:
    """
    Combines text and content from multiple documents, text files, and images
    into a single consolidated Word (.docx) document.
    """
    if not file_paths:
        raise ValueError("No se proporcionaron archivos para unir en Word.")

    import docx
    from docx.shared import Inches, Pt, RGBColor

    paths = [Path(p).resolve() for p in file_paths]
    first_p = paths[0]
    if output_docx:
        out_p = Path(output_docx)
        if out_p.is_dir() or not out_p.suffix:
            target_base = out_p / f"{first_p.stem}_combinado.docx"
        else:
            target_base = out_p
    else:
        target_base = first_p.parent / f"{first_p.stem}_combinado.docx"
    target_docx = get_unique_target_path(target_base)

    master_doc = docx.Document()
    
    # Document title
    p_title = master_doc.add_paragraph()
    r_title = p_title.add_run(f"Documento Consolidado: {len(paths)} Archivos")
    r_title.font.name = "Segoe UI"
    r_title.font.size = Pt(18)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x2B, 0x57, 0x9A)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        for idx, p in enumerate(paths):
            if not p.exists():
                continue

            ext = p.suffix.lower()

            # Section heading for this file
            master_doc.add_heading(f"{idx + 1}. {p.name}", level=2)

            # Image: insert picture directly
            if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}:
                try:
                    with Image.open(p) as img:
                        # Convert to PNG for reliable Word embedding
                        tmp_img = tmp_path / f"img_{idx}.png"
                        img.convert("RGB").save(tmp_img, "PNG")
                        master_doc.add_picture(str(tmp_img), width=Inches(5.5))
                except Exception:
                    master_doc.add_paragraph(f"(No se pudo incrustar la imagen {p.name})")

            # PDF: extract text and paragraphs
            elif ext == ".pdf":
                try:
                    reader = pypdf.PdfReader(str(p))
                    for page in reader.pages:
                        t = page.extract_text()
                        if t:
                            for para in t.split("\n\n"):
                                if para.strip():
                                    master_doc.add_paragraph(para.strip())
                except Exception:
                    master_doc.add_paragraph(f"(No se pudo extraer texto del PDF {p.name})")

            # Word document: append paragraphs
            elif ext == ".docx":
                try:
                    sub_doc = docx.Document(str(p))
                    for para in sub_doc.paragraphs:
                        if para.text.strip():
                            master_doc.add_paragraph(para.text)
                except Exception:
                    master_doc.add_paragraph(f"(No se pudo leer el documento {p.name})")

            # Spreadsheet: read and create table
            elif ext in {".xlsx", ".xls", ".csv", ".tsv"}:
                try:
                    from shiftdrop.core.excel_ops import read_spreadsheet_data
                    _, rows = read_spreadsheet_data(p)
                    if rows:
                        max_cols = min(max(len(r) for r in rows), 8)
                        table = master_doc.add_table(rows=min(len(rows), 50), cols=max_cols)
                        table.style = "Table Grid"
                        for r_i, row in enumerate(rows[:50]):
                            for c_i in range(max_cols):
                                cell_val = row[c_i] if c_i < len(row) else ""
                                table.cell(r_i, c_i).text = str(cell_val)
                except Exception:
                    pass

            # Text / plain file
            else:
                try:
                    from shiftdrop.core.doc_ops import _read_text_robust
                    text = _read_text_robust(p)
                    for line in text.splitlines():
                        if line.strip():
                            master_doc.add_paragraph(line)
                except Exception:
                    pass

            # Page break between files (except the last one)
            if idx < len(paths) - 1:
                master_doc.add_page_break()

    master_doc.save(str(target_docx))
    return target_docx


def batch_convert_to_pdf(
    file_paths: list[Path | str],
    output_dir: Optional[Path | str] = None
) -> list[Path]:
    """Converts every file in the list to its own separate PDF."""
    results = []
    for p in file_paths:
        p = Path(p)
        ext = p.suffix.lower()
        if ext == ".pdf":
            results.append(compress_pdf(p, output_dir=output_dir))
        elif ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".ico"}:
            results.append(convert_image(p, "pdf", output_dir=output_dir))
        elif ext in {".xlsx", ".xls", ".xlsm", ".csv", ".tsv", ".ods"}:
            results.append(excel_to_pdf(p, output_dir=output_dir))
        else:
            results.append(doc_to_pdf(p, output_dir=output_dir))
    return results


def batch_convert_to_docx(
    file_paths: list[Path | str],
    output_dir: Optional[Path | str] = None
) -> list[Path]:
    """Converts every file in the list to its own separate Word (.docx) document."""
    results = []
    for p in file_paths:
        p = Path(p)
        ext = p.suffix.lower()
        if ext == ".pdf":
            results.append(pdf_to_docx(p, output_dir=output_dir))
        elif ext in {".xlsx", ".xls", ".xlsm", ".csv", ".tsv", ".ods"}:
            results.append(excel_to_docx(p, output_dir=output_dir))
        elif ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}:
            # Wrap image in a docx
            import docx
            out_d = Path(output_dir) if output_dir else p.parent
            target_docx = get_unique_target_path(out_d / f"{p.stem}.docx")
            doc = docx.Document()
            doc.add_heading(p.stem, level=1)
            doc.add_picture(str(p), width=docx.shared.Inches(5.5))
            doc.save(str(target_docx))
            results.append(target_docx)
        else:
            results.append(doc_to_docx(p, output_dir=output_dir))
    return results


def batch_convert_to_images(
    file_paths: list[Path | str],
    output_format: str = "png",
    output_dir: Optional[Path | str] = None
) -> list[Path]:
    """Converts or renders every file in the list into images."""
    results = []
    for p in file_paths:
        p = Path(p)
        ext = p.suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".ico", ".gif"}:
            results.append(convert_image(p, output_format, output_dir=output_dir))
        elif ext == ".pdf":
            results.extend(pdf_to_images(p, output_format=output_format, output_dir=output_dir))
        elif ext in {".xlsx", ".xls", ".csv", ".tsv"}:
            with tempfile.TemporaryDirectory() as td:
                temp_pdf = excel_to_pdf(p, output_dir=td)
                results.extend(pdf_to_images(temp_pdf, output_format=output_format, output_dir=output_dir))
        else:
            with tempfile.TemporaryDirectory() as td:
                temp_pdf = doc_to_pdf(p, output_dir=td)
                results.extend(pdf_to_images(temp_pdf, output_format=output_format, output_dir=output_dir))
    return results


def batch_extract_text(
    file_paths: list[Path | str],
    output_dir: Optional[Path | str] = None
) -> list[Path]:
    """Extracts text from every file in the list to individual .txt files."""
    results = []
    for p in file_paths:
        p = Path(p)
        ext = p.suffix.lower()
        if ext in {".xlsx", ".xls", ".csv", ".tsv"}:
            results.append(excel_to_csv(p, output_dir=output_dir))
        elif ext in {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".webm"}:
            from shiftdrop.core.transcribe_ops import transcribe_to_txt
            results.append(transcribe_to_txt(p, output_dir=output_dir))
        else:
            results.append(doc_to_txt(p, output_dir=output_dir))
    return results
