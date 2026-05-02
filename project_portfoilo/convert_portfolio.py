"""
Convert PersonalSkin_portfolio.md to Word (.docx) and PDF formats.
"""
import re
import os
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

BASE_DIR = Path(__file__).parent
MD_FILE = BASE_DIR / "PersonalSkin_portfolio.md"
DOCX_FILE = BASE_DIR / "PersonalSkin_project_doc.docx"
PDF_FILE = BASE_DIR / "PersonalSkin_project_doc.pdf"


def read_md():
    return MD_FILE.read_text(encoding="utf-8")


def create_docx(md_text: str):
    doc = Document()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "David"
    font.size = Pt(12)

    # RTL for paragraphs
    for section in doc.sections:
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    lines = md_text.split("\n")
    in_code_block = False
    code_lines = []
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return
        # Filter out separator rows
        data_rows = [r for r in table_rows if not all(c.strip().replace("-", "").replace(":", "") == "" for c in r)]
        if not data_rows:
            in_table = False
            table_rows = []
            return
        max_cols = max(len(r) for r in data_rows)
        table = doc.add_table(rows=len(data_rows), cols=max_cols)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row_data in enumerate(data_rows):
            for j, cell_text in enumerate(row_data):
                if j < max_cols:
                    cell = table.cell(i, j)
                    cell.text = cell_text.strip()
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        for run in paragraph.runs:
                            run.font.size = Pt(10)
        # Bold first row (header)
        if data_rows:
            for cell in table.rows[0].cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.bold = True
        doc.add_paragraph()
        in_table = False
        table_rows = []

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                # End code block
                code_text = "\n".join(code_lines)
                p = doc.add_paragraph()
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(code_text)
                run.font.name = "Courier New"
                run.font.size = Pt(9)
                code_lines = []
                in_code_block = False
            else:
                flush_table()
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Table rows
        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            cells = [c.strip() for c in line.split("|")[1:-1]]  # skip first/last empty
            table_rows.append(cells)
            continue
        else:
            if in_table:
                flush_table()

        # Headers
        if line.startswith("# ") and not line.startswith("# תוכן"):
            flush_table()
            text = re.sub(r"\{#[^}]+\}", "", line[2:]).strip()
            text = text.replace("**", "")
            p = doc.add_heading(text, level=1)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue
        if line.startswith("## "):
            flush_table()
            text = re.sub(r"\{#[^}]+\}", "", line[3:]).strip()
            text = text.replace("**", "")
            p = doc.add_heading(text, level=2)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue
        if line.startswith("### "):
            flush_table()
            text = re.sub(r"\{#[^}]+\}", "", line[4:]).strip()
            text = text.replace("**", "")
            p = doc.add_heading(text, level=3)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue
        if line.startswith("#### "):
            flush_table()
            text = re.sub(r"\{#[^}]+\}", "", line[5:]).strip()
            text = text.replace("**", "")
            p = doc.add_heading(text, level=4)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue

        # Horizontal rule
        if line.strip() == "---":
            doc.add_paragraph("─" * 60)
            continue

        # Empty line
        if line.strip() == "":
            continue

        # Blockquote
        if line.startswith("> "):
            text = line[2:].strip()
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            text = re.sub(r"\*(.+?)\*", r"\1", text)
            p = doc.add_paragraph(text, style="Quote") if "Quote" in [s.name for s in doc.styles] else doc.add_paragraph(text)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue

        # List items
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            text = re.sub(r"^[\s]*[-*]\s+", "", line)
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            text = re.sub(r"`(.+?)`", r"\1", text)
            text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
            p = doc.add_paragraph(text, style="List Bullet")
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue

        if re.match(r"^\s*\d+\.\s+", line):
            text = re.sub(r"^\s*\d+\.\s+", "", line)
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            text = re.sub(r"`(.+?)`", r"\1", text)
            text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
            p = doc.add_paragraph(text, style="List Number")
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            continue

        # Regular paragraph
        text = line.strip()
        # Remove markdown links
        text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)

        # Handle bold
        bold_parts = re.split(r"\*\*(.+?)\*\*", text)
        if len(bold_parts) > 1:
            p = doc.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for i, part in enumerate(bold_parts):
                if part:
                    run = p.add_run(part)
                    if i % 2 == 1:  # odd indices are bold
                        run.bold = True
        else:
            # Handle inline code
            text = re.sub(r"`(.+?)`", r"\1", text)
            p = doc.add_paragraph(text)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    flush_table()
    doc.save(str(DOCX_FILE))
    print(f"✅ Word saved: {DOCX_FILE}")


def create_pdf_from_docx():
    """Create PDF by converting the Word document using docx2pdf (requires MS Word)."""
    try:
        from docx2pdf import convert
        convert(str(DOCX_FILE), str(PDF_FILE))
        print(f"✅ PDF saved: {PDF_FILE}")
    except Exception as e:
        print(f"⚠️  docx2pdf failed ({e}). Trying COM automation...")
        try:
            import comtypes.client
            word = comtypes.client.CreateObject("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(DOCX_FILE.resolve()))
            doc.SaveAs(str(PDF_FILE.resolve()), FileFormat=17)  # 17 = wdFormatPDF
            doc.Close()
            word.Quit()
            print(f"✅ PDF saved: {PDF_FILE}")
        except Exception as e2:
            print(f"❌ PDF generation failed: {e2}")
            print("   You can open the .docx in Word and 'Save As PDF' manually.")


if __name__ == "__main__":
    md_text = read_md()
    print("Creating Word document...")
    create_docx(md_text)
    print("Creating PDF document...")
    create_pdf_from_docx()
    print("\nDone!")





