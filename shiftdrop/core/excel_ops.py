"""
Excel and Spreadsheet Operations: Conversions between Excel (.xlsx, .xls), CSV, PDF, Word, JSON, and HTML.
100% offline, with native Excel COM acceleration when available and pure Python fallback.
"""
import os
import csv
import json
from pathlib import Path
from typing import Optional, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from shiftdrop.core.path_utils import get_unique_target_path


def _detect_encoding_and_delimiter(file_path: Path) -> tuple[str, str]:
    """Detects encoding and delimiter for CSV/TSV files."""
    raw = file_path.read_bytes()[:16384]
    
    # Detect encoding
    encoding = "utf-8"
    if raw.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    else:
        try:
            raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            try:
                import charset_normalizer
                match = charset_normalizer.from_bytes(raw).best()
                if match:
                    encoding = match.encoding
            except Exception:
                encoding = "latin1"

    # Detect delimiter
    sample_text = raw.decode(encoding, errors="replace")
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample_text, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except Exception:
        # Fallback count
        counts = {d: sample_text.count(d) for d in [",", ";", "\t", "|"]}
        delimiter = max(counts, key=counts.get) if any(counts.values()) else ","

    return encoding, delimiter


def read_spreadsheet_data(input_path: Path | str) -> tuple[str, list[list[Any]]]:
    """
    Reads data from an .xlsx, .csv, or .tsv file.
    Returns (title, rows) where rows is a list of lists of cell values.
    """
    p = Path(input_path)
    ext = p.suffix.lower()

    if ext in (".csv", ".tsv", ".txt"):
        encoding, delimiter = _detect_encoding_and_delimiter(p)
        rows: list[list[Any]] = []
        with open(p, "r", encoding=encoding, errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                rows.append(row)
        return p.stem, rows

    elif ext in (".xlsx", ".xlsm", ".xltx"):
        wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
        sheet = wb.active or wb.worksheets[0]
        sheet_title = sheet.title
        rows = []
        for row in sheet.iter_rows(values_only=True):
            # Convert None to empty string or preserve values
            rows.append([("" if val is None else str(val)) for val in row])
        wb.close()
        # Filter out trailing completely empty rows
        while rows and not any(rows[-1]):
            rows.pop()
        return sheet_title, rows

    else:
        # Try openpyxl first, then csv fallback
        try:
            wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
            sheet = wb.active or wb.worksheets[0]
            sheet_title = sheet.title
            rows = []
            for row in sheet.iter_rows(values_only=True):
                rows.append([("" if val is None else str(val)) for val in row])
            wb.close()
            return sheet_title, rows
        except Exception:
            encoding, delimiter = _detect_encoding_and_delimiter(p)
            rows = []
            with open(p, "r", encoding=encoding, errors="replace", newline="") as f:
                reader = csv.reader(f, delimiter=delimiter)
                for row in reader:
                    rows.append(row)
            return p.stem, rows


def _render_pdf_reportlab(title: str, rows: list[list[Any]], target_pdf: Path) -> Path:
    """Renders tabular data as a clean vector PDF using ReportLab."""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    if not rows:
        rows = [["(Hoja de cálculo vacía)"]]

    # Normalize column count across all rows
    max_cols = max(len(r) for r in rows) if rows else 1
    normalized_rows = []
    for r in rows:
        row_cells = list(r)
        while len(row_cells) < max_cols:
            row_cells.append("")
        # Truncate overly long single cell texts for PDF layout
        normalized_rows.append([str(c)[:150] for c in row_cells])

    # Choose orientation: landscape if more than 5 columns
    page_size = landscape(letter) if max_cols > 5 else letter
    margin = 36  # 0.5 inch

    doc = SimpleDocTemplate(
        str(target_pdf),
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ExcelTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#107C41"),
        spaceAfter=10
    )

    cell_style = ParagraphStyle(
        "ExcelCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#212121")
    )

    header_cell_style = ParagraphStyle(
        "ExcelHeaderCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    table_data = []
    for i, row in enumerate(normalized_rows):
        row_paragraphs = []
        is_header = (i == 0)
        style = header_cell_style if is_header else cell_style
        for cell in row:
            row_paragraphs.append(Paragraph(str(cell) if str(cell) else " ", style))
        table_data.append(row_paragraphs)

    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#107C41")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F9FBF9"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D7D0")),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]))

    story = [
        Paragraph(f"<b>{title}</b>", title_style),
        Spacer(1, 10),
        t
    ]
    doc.build(story)
    return target_pdf


def excel_to_pdf(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Converts Excel (.xlsx, .xls) or CSV to PDF.
    First tries Excel COM for 1:1 pixel-perfect export; fallbacks cleanly to ReportLab.
    """
    input_path = Path(input_path).resolve()
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}.pdf"
    if base_target.resolve() == input_path.resolve():
        base_target = out_dir / f"{input_path.stem}_converted.pdf"
    target_pdf = get_unique_target_path(base_target)

    # 1. Try Excel COM if running on Windows and input is .xlsx or .xls
    if input_path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        excel = None
        wb = None
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            excel.AutomationSecurity = 3  # 3 = msoAutomationSecurityForceDisable
            wb = excel.Workbooks.Open(str(input_path), ReadOnly=True)
            # 0 corresponds to xlTypePDF
            wb.ExportAsFixedFormat(0, str(target_pdf))
            wb.Close(SaveChanges=False)
            wb = None
            excel.Quit()
            excel = None
            if target_pdf.exists() and target_pdf.stat().st_size > 0:
                return target_pdf
        except Exception:
            pass
        finally:
            if wb is not None:
                try: wb.Close(SaveChanges=False)
                except Exception: pass
            if excel is not None:
                try: excel.Quit()
                except Exception: pass

    # 2. Pure offline ReportLab fallback
    title, rows = read_spreadsheet_data(input_path)
    return _render_pdf_reportlab(title, rows, target_pdf)


def excel_to_docx(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Converts an Excel (.xlsx, .xls) or CSV spreadsheet to a styled Word table (.docx).
    """
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_docx = get_unique_target_path(out_dir / f"{input_path.stem}.docx")

    title, rows = read_spreadsheet_data(input_path)

    doc = docx.Document()

    # Document Header
    p_title = doc.add_paragraph()
    run_title = p_title.add_run(f"Tabla de Datos: {title}")
    run_title.font.name = "Segoe UI"
    run_title.font.size = Pt(16)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x10, 0x7C, 0x41)  # Excel Green

    if not rows:
        doc.add_paragraph("(Hoja de cálculo sin registros)")
        doc.save(str(target_docx))
        return target_docx

    max_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=max_cols)
    table.style = "Table Grid"

    for r_idx, row in enumerate(rows):
        is_header = (r_idx == 0)
        for c_idx in range(max_cols):
            val = row[c_idx] if c_idx < len(row) else ""
            cell = table.cell(r_idx, c_idx)
            cell.text = str(val) if val is not None else ""
            
            p = cell.paragraphs[0]
            if is_header:
                for run in p.runs:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                # Background fill for header
                tcPr = cell._tc.get_or_add_tcPr()
                shd = OxmlElement('w:shd')
                shd.set(qn('w:val'), 'clear')
                shd.set(qn('w:color'), 'auto')
                shd.set(qn('w:fill'), '107C41')
                tcPr.append(shd)
            elif r_idx % 2 == 1:
                tcPr = cell._tc.get_or_add_tcPr()
                shd = OxmlElement('w:shd')
                shd.set(qn('w:val'), 'clear')
                shd.set(qn('w:color'), 'auto')
                shd.set(qn('w:fill'), 'F4F8F4')
                tcPr.append(shd)

    doc.save(str(target_docx))
    return target_docx


def excel_to_csv(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """Converts an Excel (.xlsx) file to standard UTF-8-SIG CSV."""
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_csv = get_unique_target_path(out_dir / f"{input_path.stem}.csv")

    title, rows = read_spreadsheet_data(input_path)

    with open(target_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    return target_csv


def excel_to_json(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Converts a spreadsheet to a JSON array of objects using the first row as keys.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_json = get_unique_target_path(out_dir / f"{input_path.stem}.json")

    title, rows = read_spreadsheet_data(input_path)

    if not rows:
        data = []
    elif len(rows) == 1:
        data = [{"col_" + str(i): str(val) for i, val in enumerate(rows[0])}]
    else:
        headers = [str(h).strip() if str(h).strip() else f"Columna_{i+1}" for i, h in enumerate(rows[0])]
        data = []
        for row in rows[1:]:
            row_dict = {}
            for i, h in enumerate(headers):
                val = row[i] if i < len(row) else ""
                row_dict[h] = val
            data.append(row_dict)

    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return target_json


def excel_to_html(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Converts a spreadsheet into a responsive modern HTML document.
    """
    import html
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_html = get_unique_target_path(out_dir / f"{input_path.stem}.html")

    title, rows = read_spreadsheet_data(input_path)

    html_content = [
        "<!DOCTYPE html>",
        "<html lang='es'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"  <title>{html.escape(title)} - ShiftDrop Export</title>",
        "  <style>",
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 2rem; background: #0f141c; color: #e6edf3; }",
        "    h1 { color: #107C41; font-size: 1.5rem; margin-bottom: 1rem; }",
        "    .table-container { overflow-x: auto; border: 1px solid #30363d; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }",
        "    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }",
        "    th { background-color: #107C41; color: #ffffff; padding: 12px 16px; font-weight: 600; }",
        "    td { padding: 10px 16px; border-bottom: 1px solid #21262d; }",
        "    tr:nth-child(even) { background-color: #161b22; }",
        "    tr:hover { background-color: #1f242c; }",
        "  </style>",
        "</head>",
        "<body>",
        f"  <h1>📊 {html.escape(title)}</h1>",
        "  <div class='table-container'>",
        "    <table>",
    ]

    if rows:
        # Header
        html_content.append("      <thead><tr>")
        for cell in rows[0]:
            html_content.append(f"        <th>{html.escape(str(cell))}</th>")
        html_content.append("      </tr></thead>")

        # Body
        html_content.append("      <tbody>")
        for row in rows[1:]:
            html_content.append("        <tr>")
            for cell in row:
                html_content.append(f"          <td>{html.escape(str(cell))}</td>")
            html_content.append("        </tr>")
        html_content.append("      </tbody>")

    html_content.extend([
        "    </table>",
        "  </div>",
        "</body>",
        "</html>"
    ])

    target_html.write_text("\n".join(html_content), encoding="utf-8")
    return target_html


def csv_to_excel(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Converts a CSV or TSV file into a formatted .xlsx workbook with styled headers and auto-column width.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_xlsx = get_unique_target_path(out_dir / f"{input_path.stem}.xlsx")

    title, rows = read_spreadsheet_data(input_path)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]  # Excel sheet title limit is 31 chars

    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="107C41", end_color="107C41", fill_type="solid")
    data_font = Font(name="Segoe UI", size=10)
    thin_border = Border(
        left=Side(style='thin', color='D0D7D0'),
        right=Side(style='thin', color='D0D7D0'),
        top=Side(style='thin', color='D0D7D0'),
        bottom=Side(style='thin', color='D0D7D0')
    )

    for r_idx, row in enumerate(rows, 1):
        for c_idx, val in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.border = thin_border
            if r_idx == 1:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.font = data_font
                cell.alignment = Alignment(vertical="center")

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(str(target_xlsx))
    return target_xlsx
