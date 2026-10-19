"""
Document Operations: 100% offline conversions for Word (.docx, .doc), RTF, TXT, and PDF.
Supports native Word COM on Windows, pdf2docx, python-docx, and pure Python fallbacks.
"""
from pathlib import Path
from typing import Optional
import warnings
import docx
import pypdf
import pythoncom
import win32com.client
from PIL import Image, ImageDraw

def _render_text_to_pdf(lines: list[str], output_pdf: Path) -> Path:
    """
    Renders lines of text into a multi-page PDF using PIL.
    Ensures PDF conversion works 100% offline even if Word is not installed.
    """
    page_w, page_h = 1240, 1754  # A4 at 150 DPI
    margin_x, margin_y = 80, 80
    line_height = 28
    lines_per_page = max(1, (page_h - 2 * margin_y) // line_height)

    pages = []
    chunk = []
    for line in lines:
        chunk.append(line)
        if len(chunk) >= lines_per_page:
            img = Image.new("RGB", (page_w, page_h), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            y = margin_y
            for l in chunk:
                draw.text((margin_x, y), l.rstrip("\r\n"), fill=(20, 20, 20))
                y += line_height
            pages.append(img)
            chunk = []

    if chunk or not pages:
        img = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        y = margin_y
        for l in chunk:
            draw.text((margin_x, y), l.rstrip("\r\n"), fill=(20, 20, 20))
            y += line_height
        pages.append(img)

    if pages:
        pages[0].save(str(output_pdf), "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    return output_pdf


def doc_to_pdf(input_path: Path | str, output_dir: Optional[Path | str] = None) -> Path:
    """
    Converts a document (.docx, .doc, .rtf, .txt, .odt) to PDF.
    Saved strictly in the same directory as the original file unless output_dir is given.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}.pdf"

    if target_path.resolve() == input_path.resolve():
        target_path = out_dir / f"{input_path.stem}_converted.pdf"

    ext = input_path.suffix.lower()

    # 1. Native MS Word COM (supports .docx, .doc, .rtf, .odt, .txt)
    word_success = False
    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        wdoc = word.Documents.Open(str(input_path.resolve()), ReadOnly=True)
        wdoc.SaveAs(str(target_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
        wdoc.Close(SaveChanges=0)
        word.Quit()
        word_success = target_path.exists() and target_path.stat().st_size > 0
    except Exception:
        word_success = False
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    if word_success:
        return target_path

    # 2. Pure Python fallback for .docx
    if ext in (".docx", ".doc"):
        try:
            doc = docx.Document(str(input_path))
            lines = []
            for p in doc.paragraphs:
                lines.append(p.text)
                if not p.text.strip():
                    lines.append("")
            _render_text_to_pdf(lines, target_path)
            if target_path.exists() and target_path.stat().st_size > 0:
                return target_path
        except Exception:
            pass

    # 3. Fallback for .txt, .rtf, or other text formats
    try:
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        _render_text_to_pdf(lines, target_path)
        if target_path.exists() and target_path.stat().st_size > 0:
            return target_path
    except Exception as e:
        raise RuntimeError(f"No se pudo convertir '{input_path.name}' a PDF: {e}")

    return target_path


def pdf_to_docx(input_path: Path | str, output_dir: Optional[Path | str] = None) -> Path:
    """
    Converts a PDF file to a Word (.docx) document.
    Utilizes pdf2docx for layout preservation, with python-docx/pypdf as fallback.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}.docx"

    # 1. Try high-fidelity pdf2docx
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from pdf2docx import Converter
            cv = Converter(str(input_path.resolve()))
            cv.convert(str(target_path.resolve()), start=0, end=None)
            cv.close()
        if target_path.exists() and target_path.stat().st_size > 0:
            try:
                d = docx.Document(str(target_path))
                if len(d.paragraphs) == 0:
                    d.add_paragraph("")
                    d.save(str(target_path))
            except Exception:
                pass
            return target_path
    except Exception:
        pass

    # 2. Resilient fallback using pypdf and python-docx
    reader = pypdf.PdfReader(str(input_path))
    doc = docx.Document()
    doc.add_heading(input_path.stem, 0)

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            for para in text.split("\n\n"):
                clean = para.strip()
                if clean:
                    doc.add_paragraph(clean)
        if i < len(reader.pages) - 1:
            doc.add_page_break()

    doc.save(str(target_path))
    return target_path


def doc_to_txt(input_path: Path | str, output_dir: Optional[Path | str] = None) -> Path:
    """
    Extracts plain text from a Word document or PDF into a .txt file.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}.txt"

    ext = input_path.suffix.lower()
    text_content = ""

    if ext in (".docx", ".doc"):
        doc = docx.Document(input_path)
        text_content = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif ext == ".pdf":
        reader = pypdf.PdfReader(str(input_path))
        pages_text = [p.extract_text() for p in reader.pages if p.extract_text()]
        text_content = "\n\n--- Página ---\n\n".join(pages_text)
    else:
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            text_content = f.read()

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(text_content)

    return target_path
