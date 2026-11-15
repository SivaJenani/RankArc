import os
import re
import logging
from typing import Any
import fitz

logger = logging.getLogger(__name__)

RASTER_QUESTION_TEXTS: dict[tuple[int, int], str] = {
    (2, 1): "Two different positions of the same dice are shown, the six faces of which are numbered from 12 to 17. Select the number that will be on the face opposite to the one showing '15'.",
    (2, 2): "The sequence of folding a piece of paper and the manner in which the folded paper has been cut is shown below. Choose a figure that would most closely resemble the unfolded form of the paper.",
    (2, 13): "Complete the pattern in fig. (X) by selecting one of the figures from the four alternatives:",
    (2, 17): "Observe the image carefully and pick the figure that is unlike the rest.",
    (2, 18): "Choose the item that does NOT belong to the group.",
    (2, 19): "Four different positions of the same dice are shown. Select the number that will be on the face opposite to the one showing '5'.",
    (2, 20): "In the following question, there is a specific relationship between the first two figures. Establish a similar relationship between the third and fourth figures by selecting a suitable figure from the given Answer Figures to replace the question mark (?).",
    (2, 21): "In the following question, there is a specific relationship between the first two figures. Establish a similar relationship between the third and fourth figures by selecting a suitable figure from the given Answer Figures to replace the question mark (?).",
    (2, 23): "Carefully observe Figure (X) and identify the answer figure in which Figure (X) is embedded in the same or rotated form.",
    (2, 51): "Examine the frequency polygon on battery life (in hours) of Mobile Phones below to answer the following question: What is the total number of phones recorded in this data?",
    (2, 66): "Read the following histogram which represents the time in minutes on x-axis and number of employees on y-axis and answer the following question: Suppose the company offers a bonus to employees who complete their task in less than 18 minutes. Find the percentage of employees eligible for the bonus.",
    (2, 69): "The following pie-chart represents the percentage-wise budget allocation across five key sectors. Analyse the distribution provided in the chart and answer the question that follows: The 'Education' sector corresponds to 25% of the total and forms an angle of 90°. If the combined contribution of Defense and Agriculture forms a sector equal in size to the Education sector, what is the ratio between the central angle of the Education sector and the combined central angle of Defense and Agriculture?",
    (2, 74): "A library tracked the number of detective novels borrowed by members from Monday to Friday in a specific week. The data is represented in the bar graph below: Thursday's and Friday's borrowings combined constitute what percentage of the total week's borrowings?",
    (3, 8): "In the following question, a matrix of numbers is given. These numbers follow a certain pattern either row-wise or column-wise. Identify this pattern and choose the missing number accordingly.",
}

SECTIONS = [
    'GENERAL INTELLIGENCE',
    'GENERAL AWARENESS',
    'QUANTITATIVE APTITUDE',
    'ENGLISH LANGUAGE',
]

def get_page_stream_blocks(page: fitz.Page) -> list[tuple[float, float, float, float, str, int, int]]:
    """
    Divide page into vertical bands by section headers.
    Within each band, return Left Column blocks (top to bottom),
    then Right Column blocks (top to bottom).
    """
    w = page.rect.width
    mid = w / 2.0
    blocks = page.get_text('blocks')
    has_banner = any(b[6] == 0 and 'HELD ON' in b[4].upper() for b in blocks)
    h_thresh = 95.0 if has_banner else 55.0

    sec_dividers = [
        b[1] for b in blocks
        if b[6] == 0 and any(s in b[4].strip().upper() for s in SECTIONS) and b[1] > 140.0
    ]
    sec_dividers.sort()

    bands = [h_thresh] + sec_dividers + [page.rect.height - 35.0]
    page_stream = []

    for i in range(len(bands) - 1):
        band_top, band_bottom = bands[i], bands[i + 1]
        left_b, right_b = [], []
        for b in blocks:
            if b[6] != 0:
                continue
            # Skip section header blocks
            if any(s in b[4].strip().upper() for s in SECTIONS):
                continue
            # Skip bottom footer page numbers
            if b[1] >= page.rect.height - 35.0 and b[4].strip().isdigit():
                continue

            b_center_y = (b[1] + b[3]) / 2.0
            if band_top <= b_center_y < band_bottom:
                if (b[0] + b[2]) / 2.0 < mid:
                    left_b.append(b)
                else:
                    right_b.append(b)

        left_b.sort(key=lambda x: x[1])
        right_b.sort(key=lambda x: x[1])
        page_stream.extend(left_b)
        page_stream.extend(right_b)

    return page_stream


def find_diagram_in_question(
    doc: fitz.Document,
    q_blocks: list[tuple[int, tuple]],  # list of (pno, block)
    paper_id: int,
    s_idx: int,
    q_num: int,
    questions_dir: str,
) -> tuple[str | None, fitz.Rect | None, int | None]:
    """
    Check if question contains a diagram:
    1. Raster images within question column rect (excluding header logo & watermark)
    2. Table grid drawings (multiple intersecting horizontal and vertical lines)
    Saves cropped diagram image and returns (image_url, crop_rect, page_num).
    """
    pages_involved = sorted(list(set(item[0] for item in q_blocks)))

    for pno in pages_involved:
        page = doc[pno]
        mid = page.rect.width / 2.0
        p_blocks = [item[1] for item in q_blocks if item[0] == pno]
        if not p_blocks:
            continue

        for col_left in [True, False]:
            col_blocks = [b for b in p_blocks if ((b[0] + b[2]) / 2.0 < mid) == col_left]
            if not col_blocks:
                continue

            col_x0 = 0.0 if col_left else mid
            col_x1 = mid if col_left else page.rect.width
            q_top = min(b[1] for b in col_blocks)
            q_bottom = max(b[3] for b in col_blocks)
            q_rect = fitz.Rect(col_x0, q_top, col_x1, q_bottom)

            # 1. Check raster images (diagrams, dice, folding, plots)
            contained_imgs = []
            for info in page.get_image_info():
                b = fitz.Rect(info['bbox'])
                if b.y1 <= 60.0:
                    continue  # header logo
                if b.width > 400.0 and b.height > 400.0:
                    continue  # watermark
                if q_rect.intersects(b):
                    contained_imgs.append(b)

            if contained_imgs:
                u = contained_imgs[0]
                for r in contained_imgs[1:]:
                    u = u | r
                crop = fitz.Rect(
                    max(0.0, u.x0 - 4.0),
                    max(0.0, u.y0 - 4.0),
                    min(page.rect.width, u.x1 + 4.0),
                    min(page.rect.height, u.y1 + 4.0),
                )
                filename = f"paper_{paper_id}_s{s_idx + 1}_q{q_num}.png"
                out_path = os.path.join(questions_dir, filename)
                pix = page.get_pixmap(clip=crop, dpi=300)
                pix.save(out_path)
                return f"/uploads/questions/{filename}", crop, pno

            # 2. Check table grid drawings (matrices, tables)
            # Find drawings that fall strictly inside this question's column area
            drawings = [
                fitz.Rect(d['rect']) for d in page.get_drawings()
                if q_rect.contains(fitz.Rect(d['rect']))
            ]
            h_lines = [r for r in drawings if r.height <= 2.5 and r.width > 10.0]
            v_lines = [r for r in drawings if r.width <= 2.5 and r.height > 10.0]

            if len(h_lines) >= 2 and len(v_lines) >= 2:
                all_grid = h_lines + v_lines
                u = all_grid[0]
                for r in all_grid[1:]:
                    u = u | r
                crop = fitz.Rect(
                    max(0.0, u.x0 - 4.0),
                    max(0.0, u.y0 - 4.0),
                    min(page.rect.width, u.x1 + 4.0),
                    min(page.rect.height, u.y1 + 4.0),
                )
                filename = f"paper_{paper_id}_s{s_idx + 1}_q{q_num}.png"
                out_path = os.path.join(questions_dir, filename)
                pix = page.get_pixmap(clip=crop, dpi=300)
                pix.save(out_path)
                return f"/uploads/questions/{filename}", crop, pno

    return None, None, None


def parse_question_from_blocks(
    q_num: int,
    q_blocks: list[tuple[int, tuple]],  # list of (pno, block)
    diag_crop: fitz.Rect | None = None,
    diag_pno: int | None = None,
) -> tuple[str, list[dict[str, Any]], str]:
    """
    Parse clean question text, options A-D, and correct answer.
    Filters out text blocks that lie inside the diagram crop so table numbers
    don't pollute question_text.
    """
    filtered_blocks = []
    for pno, b in q_blocks:
        if diag_crop and diag_pno is not None and pno == diag_pno:
            b_rect = fitz.Rect(b[0], b[1], b[2], b[3])
            # If block is inside or largely overlapping with diagram crop, exclude it
            if diag_crop.contains(b_rect) or (
                diag_crop.intersects(b_rect) and (b_rect & diag_crop).get_area() > 0.5 * b_rect.get_area()
            ):
                continue
        filtered_blocks.append(b)

    all_text = '\n'.join(b[4] for b in filtered_blocks)

    # 1. Correct answer
    ans_m = re.search(r'\bAns\b[:\s.]*([A-D])\b', all_text, re.IGNORECASE)
    correct_ans = ans_m.group(1).upper() if ans_m else 'A'

    # 2. Extract options
    opt_matches = list(re.finditer(r'\(([A-D])\)', all_text))
    options: list[dict[str, Any]] = []

    if len(opt_matches) >= 4:
        first_opt_pos = opt_matches[0].start()
        q_text_raw = all_text[:first_opt_pos]
        opt_text_full = all_text[first_opt_pos:]
        # Remove Ans: X
        opt_text_full = re.sub(r'\bAns\b[:\s.]*[A-D]\b.*$', '', opt_text_full, flags=re.IGNORECASE | re.DOTALL)
        parts = re.findall(r'\(([A-D])\)\s*([^(\n]+(?:\n(?!\([A-D]\)|Ans:)[^(\n]+)*)', opt_text_full)
        opt_dict = {}
        for lbl, txt in parts:
            clean_txt = ' '.join(txt.strip().split())
            if lbl.upper() not in opt_dict:
                opt_dict[lbl.upper()] = clean_txt
        for lbl in ['A', 'B', 'C', 'D']:
            txt = opt_dict.get(lbl, '')
            if not txt:
                txt = f'Option {lbl}'
            options.append({
                'label': lbl,
                'option_text': txt,
                'is_correct': (lbl == correct_ans),
            })
    else:
        q_text_raw = re.sub(r'\bAns\b[:\s.]*[A-D]\b.*$', '', all_text, flags=re.IGNORECASE | re.DOTALL)
        options = [
            {'label': l, 'option_text': f'Option {l}', 'is_correct': (l == correct_ans)}
            for l in ['A', 'B', 'C', 'D']
        ]

    # Clean question text: strip leading '01. ' or '1. '
    q_text_clean = re.sub(rf'^\s*0*{q_num}\.\s*', '', q_text_raw.strip())
    q_text_clean = ' '.join(q_text_clean.split())
    if not q_text_clean:
        q_text_clean = "Refer to the image/diagram below to answer the question:"

    return q_text_clean, options, correct_ans


def extract_exam_paper(
    pdf_path: str,
    paper_id: int,
    uploads_dir: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Robust multi-shift extraction:
    - Extracts all 7 shifts and 100 questions per shift (700 total).
    - Extracts diagrams/images as PNGs.
    - Cleans table data from question stems.
    - Returns (meta, all_questions).
    """
    questions_dir = os.path.join(uploads_dir, "questions")
    os.makedirs(questions_dir, exist_ok=True)

    doc = fitz.open(pdf_path)

    # 1. Detect shift starts
    shift_starts: list[tuple[int, str]] = []
    for pno, page in enumerate(doc):
        for b in page.get_text('blocks'):
            if b[6] == 0 and 'HELD ON' in b[4].upper():
                raw = b[4].strip().replace('\n', ' ')
                m = re.search(r'HELD\s*ON[:\s]*([^\)]+)', raw, re.IGNORECASE)
                lbl = m.group(1).strip() if m else raw
                shift_starts.append((pno, lbl))

    if not shift_starts:
        # Fallback to single set if not multi-shift
        shift_starts = [(0, "Mock Exam 1")]

    paper_sets = [{"label": stitle, "q_count": 100} for _, stitle in shift_starts]

    categories = [
        {"name": "General Intelligence", "q_start": 1, "q_end": 25, "count": 25},
        {"name": "General Awareness", "q_start": 26, "q_end": 50, "count": 25},
        {"name": "Quantitative Aptitude (Basic Arithmetic Skill)", "q_start": 51, "q_end": 75, "count": 25},
        {"name": "English Language (Basic Knowledge)", "q_start": 76, "q_end": 100, "count": 25},
    ]

    meta = {
        "exam_title": "SSC CGL 2026 Mock Test Series",
        "categories": categories,
        "paper_sets": paper_sets,
        "duration_minutes": 60,
    }

    all_questions: list[dict[str, Any]] = []

    for s_idx, (start_p, stitle) in enumerate(shift_starts):
        end_p = shift_starts[s_idx + 1][0] if s_idx + 1 < len(shift_starts) else len(doc)

        stream: list[tuple[int, tuple]] = []
        for pno in range(start_p, end_p):
            for b in get_page_stream_blocks(doc[pno]):
                stream.append((pno, b))

        # Strictly locate sequential questions 1..100
        q_indices: list[tuple[int, int]] = []
        expected = 1
        for idx, (pno, b) in enumerate(stream):
            lines = [ln.strip() for ln in b[4].strip().splitlines() if ln.strip()]
            if not lines:
                continue
            m = re.match(rf'^(?:0*{expected})\.\s*(.*)$', lines[0])
            if m:
                q_indices.append((expected, idx))
                expected += 1
                if expected > 100:
                    break

        for q_i, (q_num, s_pos) in enumerate(q_indices):
            e_pos = q_indices[q_i + 1][1] if q_i + 1 < len(q_indices) else len(stream)
            q_blocks = stream[s_pos:e_pos]

            image_url, diag_crop, diag_pno = find_diagram_in_question(
                doc, q_blocks, paper_id, s_idx, q_num, questions_dir
            )

            q_text, options, correct_ans = parse_question_from_blocks(
                q_num, q_blocks, diag_crop, diag_pno
            )

            # Override with exact question text if it was baked into a raster image
            key = (s_idx + 1, q_num)
            if key in RASTER_QUESTION_TEXTS:
                q_text = RASTER_QUESTION_TEXTS[key]
            else:
                # Clean any stray formatting artifacts
                q_text = re.sub(r'\s*DIAGRAM_OR_GEOMETRIC.*$', '', q_text).strip()
                q_text = re.sub(r'\s*\([A-D]\).*$', '', q_text).strip()

            all_questions.append({
                "question_number": q_num,
                "question_text": q_text,
                "question_type": "mcq",
                "image_url": image_url,
                "paper_set": stitle,
                "options": options,
                "explanation": None,
            })

    return meta, all_questions
