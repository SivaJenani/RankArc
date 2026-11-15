"""Conservative answer-key import. Parsing proposes; the owner reviews before apply."""
import re
from pathlib import Path

PAIR = re.compile(r"(?<![\w.])(\d{1,4})\s*[.):,=\-]?\s*\(?([A-E])\)?(?![A-Za-z])", re.I)


def parse_key(text):
    entries = []
    for match in PAIR.finditer(text):
        entries.append({'number': int(match[1]), 'label': match[2].upper()})
    if not entries:
        raise ValueError('No question-number / A-E pairs found. Use one pair per line, for example 1 B. Check the selected file.')
    if len(entries) > 2000:
        raise ValueError('Answer keys are limited to 2000 entries.')
    return entries


def read_key(path):
    ext = Path(path).suffix.lower()
    if ext in {'.txt', '.csv'}:
        try:
            return Path(path).read_text(encoding='utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('Save this text key as UTF-8 or upload a PDF.') from exc
    if ext == '.docx':
        from app.services.parser import extract_text_from_docx
        return extract_text_from_docx(path)
    import pytesseract
    from PIL import Image
    if ext in {'.png', '.jpg', '.jpeg'}:
        with Image.open(path) as image:
            if image.width * image.height > 25000000:
                raise ValueError('Key images must be at most 25 megapixels.')
            return pytesseract.image_to_string(image, config='--psm 6', timeout=90)
    if ext == '.pdf':
        import fitz
        chunks = []
        with fitz.open(path) as doc:
            if doc.needs_pass or len(doc) > 20:
                raise ValueError('Upload an unlocked answer key with at most 20 pages.')
            for page in doc:
                text = page.get_text(sort=True)
                if len(text.strip()) < 20:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
                    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                    text = pytesseract.image_to_string(image, config='--psm 6', timeout=90)
                chunks.append(text)
        return '\n'.join(chunks)
    raise ValueError('Use PDF, DOCX, TXT, CSV, PNG or JPG for the answer key.')


def validate_mapping(entries, questions):
    # questions: [{number, labels, ...}]. Never infer an offset or renumber a key.
    errors, seen, lookup = [], {}, {}
    for q in questions:
        n = q['number']
        if n in lookup:
            errors.append(f'Question number {n} occurs in more than one set. Upload one uniquely numbered set at a time.')
        lookup[n] = q
    for item in entries:
        n, label = item['number'], item['label']
        if n in seen:
            errors.append(f'Duplicate key entry for question {n}.')
        seen[n] = label
        if n not in lookup:
            errors.append(f'Key question {n} does not exist in this paper.')
        elif label not in lookup[n]['labels']:
            errors.append(f'Question {n} has no option {label}.')
    missing = sorted(set(lookup) - set(seen))
    if missing:
        errors.append('Missing key answers for questions: ' + ', '.join(map(str, missing[:40])) + ('...' if len(missing) > 40 else ''))
    return errors
