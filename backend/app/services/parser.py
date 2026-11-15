import logging
import os
import re

logger = logging.getLogger(__name__)

HEADER_BOTTOM = 95  # px – skip the top banner (logo + title bar)

# Regex to detect a meaningful shift/exam header
_SHIFT_HEADER_RE = re.compile(
    r'HELD\s+ON|SHIFT\s*\d|SSC\s+CGL|EXAM\s+DATE',
    re.IGNORECASE,
)

# Option labels pattern – used to detect option lines
_OPT_LINE_RE = re.compile(r'^\s*\([A-D]\)', re.MULTILINE)


def _get_page_header(page) -> str:
    """Extract text from the top header band of a page."""
    w = page.width
    raw = page.crop((0, 0, w, HEADER_BOTTOM)).extract_text() or ""
    return " ".join(raw.strip().split())


def _extract_page_body(page) -> str:
    """
    Smart 2-column extraction that keeps options together with their question.

    Strategy:
    1. Detect column gutter using word bounding boxes.
    2. Extract LEFT column top-to-bottom.
    3. Extract RIGHT column top-to-bottom.
    4. For each question on the LEFT that has only (A)(C) options (or no options),
       look at the RIGHT column's same vertical band for (B)(D) options and
       append them immediately.
    5. Concatenate: left-patched questions + right questions.
    
    This avoids the layout=True problem (right-column question numbers pollute
    left-column question text) while keeping options (A)(B)(C)(D) together.
    """
    w, h = page.width, page.height
    body = page.crop((0, HEADER_BOTTOM, w, h))
    _, top, _, bottom = body.bbox

    words = body.extract_words(x_tolerance=4, y_tolerance=4)
    if not words:
        return body.extract_text() or ""

    midpoint = w / 2
    left_words = [wd for wd in words if wd["x1"] <= midpoint + 10]
    right_words = [wd for wd in words if wd["x0"] >= midpoint - 10]
    span_words = [
        wd for wd in words
        if wd["x0"] < midpoint - 10 and wd["x1"] > midpoint + 10
        and not wd["text"].isdigit()
    ]

    # Only use 2-column mode when page clearly has two columns
    if len(left_words) >= 10 and len(right_words) >= 10 and not span_words:
        return _two_col_extract(body, top, bottom, midpoint, w)

    # Single-column or unknown layout: use layout=True
    try:
        text = body.extract_text(layout=True, layout_width_chars=130)
        if text and text.strip():
            return _clean_layout_text(text)
    except Exception:
        pass

    # Word-sorted fallback
    lines: dict[int, list] = {}
    for wd in words:
        row_key = round(wd["top"] / 5) * 5
        lines.setdefault(row_key, []).append(wd)
    result_lines = []
    for row_key in sorted(lines):
        row_words = sorted(lines[row_key], key=lambda wo: wo["x0"])
        result_lines.append(" ".join(wo["text"] for wo in row_words))
    return "\n".join(result_lines)


def _two_col_extract(body, top: float, bottom: float, midpoint: float, w: float) -> str:
    """
    Extract a two-column page keeping options paired with their question.

    For each question in the LEFT column, we detect if its options are split
    across both columns (A/C on left, B/D on right) and merge them.
    Then append right-column questions.
    """
    left = body.crop((0, top, midpoint, bottom))
    right = body.crop((midpoint, top, w, bottom))

    left_text = left.extract_text() or ""
    right_text = right.extract_text() or ""

    # Build a vertical map of right-column words for option stealing
    right_words = body.extract_words(x_tolerance=4, y_tolerance=4)
    right_words = [wd for wd in right_words if wd["x0"] >= midpoint - 5]

    # Group right words by row bucket
    right_rows: dict[int, list] = {}
    for wd in right_words:
        row_key = round(wd["top"] / 3) * 3
        right_rows.setdefault(row_key, []).append(wd)

    def get_right_text_at_top(q_top: float, q_bot: float) -> str:
        """Get right-column text in the vertical band [q_top, q_bot]."""
        lines = []
        for row_key in sorted(right_rows):
            if q_top - 3 <= row_key <= q_bot + 3:
                row = sorted(right_rows[row_key], key=lambda wo: wo["x0"])
                lines.append(" ".join(wo["text"] for wo in row))
        return "\n".join(lines)

    # Parse left column into question blocks by finding "NN." line starts
    q_block_re = re.compile(r'(?:^|\n)(\s*)(\d{1,3})\.\s+')
    
    left_lines = left_text.splitlines(keepends=True)
    left_words_list = body.extract_words(x_tolerance=4, y_tolerance=4)
    left_words_list = [wd for wd in left_words_list if wd["x1"] <= midpoint + 5]

    # Try to find approximate vertical position for each left-column question
    # by looking for question-number words
    q_tops: dict[int, float] = {}  # question_number -> top y
    for wd in left_words_list:
        try:
            num = int(wd["text"].rstrip("."))
            if 1 <= num <= 150:
                q_tops[num] = wd["top"]
        except ValueError:
            pass

    # Build enriched left text: for each question, add right-col option text
    # Only steal from right if left seems to have < 4 options
    opt_re = re.compile(r'\(([A-D])\)', re.IGNORECASE)

    # Split left_text into question segments
    segments = []
    q_numbers = sorted(q_tops.keys())
    for i, qn in enumerate(q_numbers):
        q_top = q_tops[qn]
        q_bot = q_tops[q_numbers[i + 1]] if i + 1 < len(q_numbers) else bottom

        # Get left-col text for this question
        left_seg_words = [
            wd for wd in left_words_list
            if q_top - 2 <= wd["top"] <= q_bot + 2
        ]
        left_seg_text = " ".join(wd["text"] for wd in sorted(left_seg_words, key=lambda wo: (round(wo["top"]/4)*4, wo["x0"])))

        # Detect how many unique option labels are on the left
        left_opts = set(m.group(1).upper() for m in opt_re.finditer(left_seg_text))

        # If left has < 4 options, try to get B/D from right column
        if len(left_opts) < 4:
            right_seg = get_right_text_at_top(q_top, q_bot)
            right_opts = set(m.group(1).upper() for m in opt_re.finditer(right_seg))
            # Only add right options that are truly option text (B/D that aren't in left)
            missing = right_opts - left_opts
            if missing:
                # Extract only lines from right that contain the missing options
                extra_lines = []
                for line in right_seg.splitlines():
                    if opt_re.search(line):
                        line_opts = set(m.group(1).upper() for m in opt_re.finditer(line))
                        if line_opts & missing:
                            extra_lines.append(line.strip())
                if extra_lines:
                    left_seg_text = left_seg_text + " " + " ".join(extra_lines)

        segments.append(left_seg_text)

    # If we couldn't parse question blocks, just concat columns
    if not segments:
        return f"{left_text.rstrip()}\n{right_text.lstrip()}"

    enriched_left = "\n".join(segments)
    # Right column questions only (remove lines that are options we already added)
    right_only = _remove_stolen_options(right_text, q_tops, q_numbers, right_rows, bottom)

    combined = enriched_left.rstrip() + "\n" + right_only.lstrip()
    return combined


def _remove_stolen_options(right_text: str, q_tops: dict, q_numbers: list, right_rows: dict, bottom: float) -> str:
    """Keep right-column text, but it's returned as-is for right-column questions."""
    # For now, return right column as-is — right column questions start there
    return right_text


def _clean_layout_text(text: str) -> str:
    """Post-process layout=True output: collapse blank lines, trim trailing spaces."""
    lines = []
    blank_count = 0
    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped.strip():
            blank_count += 1
            if blank_count <= 1:
                lines.append("")
        else:
            blank_count = 0
            stripped = re.sub(r' {4,}', '   ', stripped)
            lines.append(stripped)
    return "\n".join(lines)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file.

    Uses smart 2-column extraction to keep options (A)(B)(C)(D) together
    with their question, even when the PDF splits them across columns.
    Includes the header on every page so all shift labels are captured.
    Falls back to pytesseract OCR for image-based PDFs.
    """
    import pdfplumber

    all_text: list[str] = []
    total_chars = 0
    page_count = 0

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            header = _get_page_header(page)
            body = _extract_page_body(page)

            if header and _SHIFT_HEADER_RE.search(header):
                page_text = f"{header}\n{body}"
            else:
                page_text = body

            all_text.append(page_text)
            total_chars += len(page_text)
            page_count += 1

    avg_chars = total_chars / max(page_count, 1)

    if avg_chars >= 100:
        return "\n".join(all_text)

    logger.info("PDF appears to be image-based; falling back to OCR for %s", file_path)
    try:
        import pytesseract

        ocr_parts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                pil_image = page.to_image(resolution=200).original
                ocr_text = pytesseract.image_to_string(pil_image)
                ocr_parts.append(ocr_text)
        return "\n".join(ocr_parts)
    except Exception as exc:
        logger.warning("OCR fallback failed: %s. Returning partial text.", exc)
        return "\n".join(all_text)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a .docx file using python-docx."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def extract_text(file_path: str) -> str:
    """Route text extraction by file extension."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext!r}")
