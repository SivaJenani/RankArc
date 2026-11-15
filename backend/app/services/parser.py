"""Local-only document reading. No paid APIs and no paper-specific templates."""
import os
import re
from collections import Counter
from pathlib import Path

QUESTION_START = re.compile(r"^\s*(?:Q(?:uestion)?\s*\.?\s*)?\d{1,4}\s*[.)、:]\s*", re.I)


def _pdf_lines(page):
    words = page.get_text("words", sort=True)
    rows = {}
    for word in words:
        rows.setdefault((word[5], word[6]), []).append(word)
    lines = []
    for row in rows.values():
        row.sort(key=lambda w: w[0])
        lines.append((min(w[0] for w in row), min(w[1] for w in row),
                      max(w[2] for w in row), max(w[3] for w in row),
                      " ".join(w[4] for w in row)))
    mid = page.rect.width / 2
    starts = [line for line in lines if QUESTION_START.match(line[4])]
    left = any(line[0] < mid - 25 for line in starts)
    right = any(line[0] > mid - 10 for line in starts)
    # Independent question starts in each column, not just options spread across a row.
    columns = left and right and not any(l[0] < mid - 25 and l[2] > mid + 25 for l in lines)
    if columns:
        lines.sort(key=lambda line: (line[0] >= mid - 10, round(line[1], 1), line[0]))
    else:
        lines.sort(key=lambda line: (round(line[1] / 3), line[0]))
    return lines, columns


def extract_text_from_pdf(file_path: str) -> str:
    import fitz
    pages = []
    with fitz.open(file_path) as doc:
        if doc.needs_pass:
            raise ValueError("This PDF is password protected. Upload an unlocked copy.")
        if len(doc) > 300:
            raise ValueError("Please split this PDF into files of at most 300 pages.")
        for index, page in enumerate(doc):
            lines, _ = _pdf_lines(page)
            text = "\n".join(line[4] for line in lines)
            # Decide per page. A text cover must not hide scanned questions later.
            if len(re.sub(r"\s", "", text)) < 40 or "\ufffd" in text:
                try:
                    import pytesseract
                    from PIL import Image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
                    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    text = pytesseract.image_to_string(image, config="--psm 3", timeout=90)
                except Exception as exc:
                    raise ValueError(
                        f"Page {index + 1} needs OCR, which is unavailable or timed out. "
                        "Upload a searchable PDF or DOCX instead."
                    ) from exc
            pages.append(text)
    # Remove only repeating margin text, never a fixed top strip of every document.
    margins = Counter()
    for text in pages:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        margins.update(set(lines[:2] + lines[-2:]))
    repeated = {line for line, n in margins.items() if n >= 3 and not QUESTION_START.match(line)
                and not re.search(r"\b(shift|held on|section|answer)\b|\([A-Ea-e]\)", line, re.I)}
    return "\n\f\n".join("\n".join(line for line in text.splitlines()
                                            if line.strip() not in repeated) for text in pages)


def extract_text_from_docx(file_path: str) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    doc = Document(file_path)
    chunks = []
    # Preserve paragraphs and tables in their original order, including merged cells.
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            chunks.append(Paragraph(child, doc).text)
        elif child.tag.endswith("}tbl"):
            for row in Table(child, doc).rows:
                seen = set()
                cells = []
                for cell in row.cells:
                    if cell._tc in seen:
                        continue
                    seen.add(cell._tc)
                    cells.append(cell.text)
                chunks.append("\n".join(cells))
    return "\n".join(chunks)


def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext == ".docx":
        return extract_text_from_docx(file_path)
    raise ValueError("Only PDF and DOCX are supported. Convert old .doc files to .docx first.")
