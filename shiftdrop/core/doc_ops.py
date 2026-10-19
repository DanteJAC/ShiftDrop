"""
Document Operations: 100% offline conversions for Word (.docx, .doc), RTF, TXT, and PDF.
Supports Word COM on Windows and standalone python-docx / pypdf fallbacks.
"""
from pathlib import Path
from typing import Optional
import docx
import pypdf
import pythoncom
import win32com.client

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

    # 1. Try native MS Word COM (supports .docx, .doc, .rtf, .odt, .txt)
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

    # 2. Fallback for .txt or if Word is not installed: create simple PDF
    if ext == ".txt":
        writer = pypdf.PdfWriter()
        # For plain text fallback: read text and convert or create PDF
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        # Minimalist PDF text generator
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1240, 1754), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        y = 60
        for line in lines[:60]:
            draw.text((60, y), line.strip(), fill=(0, 0, 0))
            y += 24
        img.save(target_path, "PDF", resolution=150.0)
        return target_path

    if not target_path.exists():
        raise RuntimeError(f"No se pudo convertir '{input_path.name}' a PDF.")

    return target_path


def pdf_to_docx(input_path: Path | str, output_dir: Optional[Path | str] = None) -> Path:
    """
    Converts a PDF file to a Word (.docx) document.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}.docx"

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

    doc.save(target_path)
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
