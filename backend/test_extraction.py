import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, r'E:\Rankly\backend')

from app.services.parser import extract_text_from_pdf
from app.services.llm_extractor import _regex_extract_meta, _split_by_sets, _regex_extract_questions

PDF = r'C:/Users/sivajenani/.gemini/antigravity/brain/bad96cca-a60e-435a-8018-df2563775815/.user_uploaded/media_1794492844207_18b4dd6a.pdf'

print("Extracting text...", flush=True)
raw = extract_text_from_pdf(PDF)
print(f"Total chars: {len(raw)}", flush=True)

print("\nExtracting meta...", flush=True)
meta = _regex_extract_meta(raw)
print(f"exam_title: {meta['exam_title']}")
print(f"duration_minutes: {meta['duration_minutes']}")
sets = meta['paper_sets']
print(f"paper_sets ({len(sets)}):")
for s in sets:
    print(f"  {s}")

print("\nSplitting by sets...", flush=True)
chunks = _split_by_sets(raw, sets)
print(f"Chunks found: {len(chunks)}")
for label, chunk in chunks:
    qs = _regex_extract_questions(chunk)
    print(f"  [{label}] chunk_len={len(chunk)} questions_found={len(qs)}")
