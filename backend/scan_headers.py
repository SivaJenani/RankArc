import pdfplumber
import warnings
import sys
warnings.filterwarnings('ignore')

PDF = r'C:/Users/sivajenani/.gemini/antigravity/brain/bad96cca-a60e-435a-8018-df2563775815/.user_uploaded/media_1794492844207_18b4dd6a.pdf'

with pdfplumber.open(PDF) as pdf:
    print(f"Total pages: {len(pdf.pages)}", flush=True)
    prev_header = None
    for i, page in enumerate(pdf.pages):
        h = page.crop((0, 0, page.width, 95)).extract_text() or ''
        h_clean = ' '.join(h.strip().split())
        if h_clean and h_clean != prev_header:
            print(f"Page {i:2d}: {h_clean[:120]}", flush=True)
            prev_header = h_clean
        elif not h_clean:
            print(f"Page {i:2d}: [NO HEADER]", flush=True)

print("Done", flush=True)
