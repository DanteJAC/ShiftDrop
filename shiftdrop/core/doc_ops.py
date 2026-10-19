"""
Document Operations: 100% offline conversions for Word (.docx, .doc), RTF, TXT, and PDF.
Supports ReportLab vector PDF generation, native Word COM on Windows, pdf2docx, and python-docx.
"""
from pathlib import Path
from typing import Optional
import warnings
import docx
import pypdf
import pythoncom
import win32com.client
from PIL import Image, ImageDraw
from shiftdrop.core.path_utils import get_unique_target_path

def _read_text_robust(path: Path | str) -> str:
    """
    Reads text with multi-encoding fallback and charset-normalizer.
    Guarantees no UnicodeDecodeError for any text file.
    """
    p = Path(path)
    raw = p.read_bytes()
    try:
        import charset_normalizer
        res = charset_normalizer.from_bytes(raw).best()
        if res and res.encoding:
            return str(res)
    except Exception:
        pass

    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1", "iso-8859-1", "utf-16", "cp437"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _render_text_to_pdf(text: str, output_pdf: Path, title: str = "") -> Path:
    """
    Renders text into a vector PDF with word wrapping, margins, and pages using ReportLab.
    Falls back to Pillow bitmap generation if ReportLab is unavailable.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib import colors

        pdf = SimpleDocTemplate(
            str(output_pdf),
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]
        normal_style.fontSize = 10
        normal_style.leading = 14
        normal_style.textColor = colors.HexColor("#1E293B")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            spaceAfter=12,
            textColor=colors.HexColor("#0F172A")
        )

        story = []
        if title:
            safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe_title, title_style))
            story.append(Spacer(1, 10))

        for line in text.splitlines():
            clean = line.strip()
            if not clean:
                story.append(Spacer(1, 6))
            else:
                safe_line = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe_line, normal_style))

        pdf.build(story)
        if output_pdf.exists() and output_pdf.stat().st_size > 0:
            return output_pdf
    except Exception:
        pass

    # Pure Pillow fallback if ReportLab fails
    lines = text.splitlines()
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
                draw.text((margin_x, y), l.rstrip("\r\n")[:100], fill=(20, 20, 20))
                y += line_height
            pages.append(img)
            chunk = []

    if chunk or not pages:
        img = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        y = margin_y
        for l in chunk:
            draw.text((margin_x, y), l.rstrip("\r\n")[:100], fill=(20, 20, 20))
            y += line_height
        pages.append(img)

    if pages:
        pages[0].save(str(output_pdf), "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    return output_pdf


def doc_to_pdf(input_path: Path | str, output_dir: Optional[Path | str] = None) -> Path:
    """
    Converts a document (.docx, .doc, .rtf, .txt, .odt, .md, .csv) to PDF.
    Saved strictly in the same directory as the original file unless output_dir is given.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}.pdf"
    if base_target.resolve() == input_path.resolve():
        base_target = out_dir / f"{input_path.stem}_converted.pdf"
    target_path = get_unique_target_path(base_target)

    ext = input_path.suffix.lower()

    # 1. Plain text formats (.txt, .md, .csv, .log): Fast, clean ReportLab generation
    if ext in (".txt", ".md", ".csv", ".log", ".rtf"):
        text = _read_text_robust(input_path)
        return _render_text_to_pdf(text, target_path, title=input_path.stem)

    # 2. Native MS Word COM for .docx, .doc, .odt
    # Uses DispatchEx for process isolation and AutomationSecurity=3 (ForceDisable macros)
    word_success = False
    word = None
    wdoc = None
    try:
        pythoncom.CoInitialize()
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = 3  # 3 = msoAutomationSecurityForceDisable
        wdoc = word.Documents.Open(str(input_path.resolve()), ReadOnly=True, ConfirmConversions=False)
        wdoc.SaveAs(str(target_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
        wdoc.Close(SaveChanges=0)
        wdoc = None
        word_success = target_path.exists() and target_path.stat().st_size > 0
    except Exception:
        word_success = False
    finally:
        if wdoc:
            try:
                wdoc.Close(SaveChanges=0)
            except Exception:
                pass
        if word:
            try:
                word.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    if word_success:
        return target_path

    # 3. Pure Python fallback for .docx / other documents
    if ext in (".docx", ".doc"):
        try:
            doc = docx.Document(str(input_path))
            paras = [p.text for p in doc.paragraphs]
            text = "\n".join(paras)
            return _render_text_to_pdf(text, target_path, title=input_path.stem)
        except Exception:
            pass

    # 4. Final text fallback
    try:
        text = _read_text_robust(input_path)
        return _render_text_to_pdf(text, target_path, title=input_path.stem)
    except Exception as e:
        raise RuntimeError(f"No se pudo convertir '{input_path.name}' a PDF: {e}")


def doc_to_docx(input_path: Path | str, output_dir: Optional[Path | str] = None) -> Path:
    """
    Converts any text file, document, or PDF to a Word (.docx) document.
    Saved strictly in the same directory as the original file unless output_dir is given.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}.docx"
    if base_target.resolve() == input_path.resolve():
        base_target = out_dir / f"{input_path.stem}_converted.docx"
    target_path = get_unique_target_path(base_target)

    ext = input_path.suffix.lower()

    # 1. If it's already a .docx: copy or return target
    if ext == ".docx":
        import shutil
        if target_path.resolve() != input_path.resolve():
            shutil.copy2(input_path, target_path)
        return target_path

    # 2. If it's a PDF: use high-fidelity pdf_to_docx
    if ext == ".pdf":
        return pdf_to_docx(input_path, output_dir=output_dir)

    # 3. Plain text formats (.txt, .md, .csv, .log, .rtf)
    if ext in (".txt", ".md", ".csv", ".log", ".rtf") or True:
        text = _read_text_robust(input_path)
        doc = docx.Document()
        doc.add_heading(input_path.stem, level=1)
        for line in text.splitlines():
            doc.add_paragraph(line)
        doc.save(str(target_path))
        return target_path


def pdf_to_docx(input_path: Path | str, output_dir: Optional[Path | str] = None) -> Path:
    """
    Converts a PDF file to a Word (.docx) document.
    Utilizes pdf2docx for layout preservation, with python-docx/pypdf as fallback.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}.docx"
    if base_target.resolve() == input_path.resolve():
        base_target = out_dir / f"{input_path.stem}_converted.docx"
    target_path = get_unique_target_path(base_target)

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
    Extracts plain text from a Word document, PDF, or text file into a .txt file.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}.txt"
    if base_target.resolve() == input_path.resolve():
        base_target = out_dir / f"{input_path.stem}_converted.txt"
    target_path = get_unique_target_path(base_target)

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
        text_content = _read_text_robust(input_path)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(text_content)

    return target_path
