"""Image-first scan extraction: OCR finds boundaries, pixels preserve the question."""
import logging
import os
import re
import uuid
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)
# Tesseract otherwise creates many threads per page on small free hosts.
os.environ.setdefault("OMP_THREAD_LIMIT", "1")


def extract_scanned_paper(pdf_path, paper_id, upload_dir, progress=None):
    import fitz
    import pytesseract
    from PIL import Image
    output = Path(upload_dir) / "questions"
    output.mkdir(parents=True, exist_ok=True)
    all_questions = []
    expected = 1
    duration = None
    title = "Scanned paper"
    ocr_pages = []
    with fitz.open(pdf_path) as doc:
        if doc.needs_pass:
            raise ValueError("Upload an unlocked PDF.")
        if len(doc) > 100:
            raise ValueError("Please split scanned PDFs into files of at most 100 pages.")
        for pno, page in enumerate(doc):
            if progress:
                progress(15 + int(60 * pno / max(len(doc), 1)), f"Reading scanned page {pno + 1}/{len(doc)} with local OCR")
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            try:
                data = pytesseract.image_to_data(image, config="--psm 6", output_type=pytesseract.Output.DICT, timeout=90)
            except Exception as exc:
                raise ValueError("This scan needs local Tesseract OCR. Install it on the server or upload a searchable PDF/DOCX.") from exc
            words = [(data["text"][i].strip(), data["left"][i], data["top"][i], data["width"][i], data["height"][i], float(data["conf"][i]))
                     for i in range(len(data["text"])) if data["text"][i].strip()]
            text = " ".join(w[0] for w in words)
            if pno == 0:
                if re.search(r"duration\s*:?\s*three\s*hours", text, re.I):
                    duration = 180
                match = re.search(r"(?:duration|time)\s*:?\s*(\d+)\s*(hours?|hrs?|minutes?|mins?)", text, re.I)
                if match:
                    duration = int(match[1]) * (60 if match[2].lower().startswith("h") else 1)
            # Instruction numbering is not question numbering. Blank backs are not questions.
            if re.search(r"important\s+instructions|space\s+for\s+rough\s+work", text, re.I):
                ocr_pages.append({"page": pno + 1, "questions": 0, "skipped": "instructions/rough work"})
                continue
            candidates = []
            for word, x, y, w, h, confidence in words:
                match = re.fullmatch(r"[^\w\d]*(\d{1,4})[.,:)]*", word)
                if match and confidence >= 20 and x < image.width * .15 and y < image.height * .91:
                    number = int(match[1])
                    if number == expected:
                        candidates.append((number, y, h))
                        expected += 1
                    elif number > expected and number <= expected + 5:
                        raise ValueError(f"OCR could not locate question {expected} before {number} on page {pno + 1}. Upload a clearer scan; no partial test was saved.")
            if not candidates:
                if all_questions and re.search(r"\([A-E]\)", text):
                    raise ValueError(f"Could not locate question boundaries on page {pno + 1}. Please review this page.")
                ocr_pages.append({"page": pno + 1, "questions": 0, "skipped": "no numbered questions"})
                continue
            # A shared passage before the page's first question accompanies every crop.
            preamble = None
            first_y = candidates[0][1]
            leading = " ".join(w[0] for w in words if w[2] < first_y)
            if first_y > image.height * .22 and re.search(r"read\b.*\b(?:passage|poem|extract|following)", leading, re.I):
                preamble = image.crop((0, max(0, min(w[2] for w in words) - 12), image.width, first_y - 12))
            for i, (number, y, height) in enumerate(candidates):
                end = candidates[i + 1][1] - 12 if i + 1 < len(candidates) else image.height
                crop = image.crop((0, max(0, y - 12), image.width, end))
                if preamble is not None:
                    combined = Image.new("RGB", (image.width, preamble.height + crop.height + 20), "white")
                    combined.paste(preamble, (0, 0)); combined.paste(crop, (0, preamble.height + 20))
                    crop = combined
                crop.thumbnail((1500, 4000))
                filename = uuid.uuid4().hex + ".png"
                crop.save(output / filename, optimize=True)
                segment = " ".join(w[0] for w in words if y - 5 <= w[2] < end)
                labels = set(re.findall(r"\(([A-E])\)", segment))
                # A-E exams often have marked/overwritten letters. An explicit E or
                # the printed 'Answer not known' fifth choice establishes five options.
                if not ("D" in labels or "E" in labels or re.search(r"answer\s+not\s+known", segment, re.I)):
                    raise ValueError(f"Could not verify the option count for question {number}. Upload a clearer scan.")
                count = 5 if "E" in labels or re.search(r"answer\s+not\s+known", segment, re.I) else 4
                all_questions.append({"question_number": number,
                    "question_text": f"Question {number} (original scan). Enlarge the image to read the wording and all options.",
                    "question_type": "mcq", "paper_set": "Paper 1",
                    "image_url": f"/api/papers/{paper_id}/assets/{filename}",
                    "options": [{"label": chr(65 + j), "option_text": f"{chr(65 + j)} - see original scan", "is_correct": False} for j in range(count)],
                    "explanation": None})
            ocr_pages.append({"page": pno + 1, "questions": len(candidates)})
        if not all_questions:
            raise ValueError("No safely numbered questions located in this scan. Upload a clearer or searchable PDF.")
    n = len(all_questions)
    meta = {"exam_title": title, "paper_sets": [{"label": "Paper 1", "q_count": n}],
            "categories": [{"name": "Scanned questions", "count": n, "q_start": 1, "q_end": n}],
            "duration_minutes": duration, "unkeyed_questions": n,
            "extraction_method": "local-tesseract-source-crops", "source_pages": ocr_pages,
            "warnings": ["Scan mode preserves original wording, tables and diagrams as images. Check every boundary and option count in Review.",
                         "The source contains visible marks. These remain in the image and may reveal answers. Use a clean unmarked paper for a realistic test.",
                         "No verified answer key was supplied. This is unscored practice until correct answers are marked in Review."]}
    return meta, all_questions
