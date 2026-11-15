"""
Spot-check Q4 and Q14 from the SSC CGL PDF after the layout=True fix.
"""
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, r'E:\Rankly\backend')

from app.services.parser import extract_text_from_pdf
from app.services.llm_extractor import _regex_extract_meta, _split_by_sets, _regex_extract_questions

PDF = r'C:/Users/sivajenani/.gemini/antigravity/brain/bad96cca-a60e-435a-8018-df2563775815/.user_uploaded/media_1794492844207_18b4dd6a.pdf'

print("Extracting text with layout=True...", flush=True)
raw = extract_text_from_pdf(PDF)

meta = _regex_extract_meta(raw)
sets = meta['paper_sets']
print(f"Detected {len(sets)} paper sets", flush=True)

chunks = _split_by_sets(raw, sets)
# Use first chunk (10 OCT 2026 SHIFT 1)
label, chunk = chunks[0]
print(f"\nShift: {label}", flush=True)

questions = _regex_extract_questions(chunk)
q_map = {q['question_number']: q for q in questions}
print(f"Total questions extracted: {len(questions)}", flush=True)

# Spot check Q4 and Q14
for qn in [1, 4, 14]:
    q = q_map.get(qn)
    if q:
        print(f"\n--- Q{qn} ---")
        print(f"Text: {q['question_text'][:200]}")
        for o in q['options']:
            mark = '✓' if o['is_correct'] else ' '
            print(f"  ({o['label']}) {o['option_text']}  {mark}")
        print(f"  Explanation: {q['explanation']}")
    else:
        print(f"\nQ{qn}: NOT FOUND")

print("\nDone", flush=True)
