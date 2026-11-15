import pdfplumber, sys

PDF_PATH = r'C:/Users/sivajenani/.gemini/antigravity/brain/bad96cca-a60e-435a-8018-df2563775815/.user_uploaded/media_1794492844207_18b4dd6a.pdf'

HEADER_BOTTOM = 95

def extract_page_layout(page):
    w, h = page.width, page.height
    body = page.crop((0, HEADER_BOTTOM, w, h))
    try:
        text = body.extract_text(layout=True, layout_width_chars=120)
        if text and text.strip():
            return text
    except Exception as e:
        print(f"layout failed: {e}")
    return body.extract_text() or ""

with pdfplumber.open(PDF_PATH) as pdf:
    # Page 0 header
    p0 = pdf.pages[0]
    header = p0.crop((0, 0, p0.width, HEADER_BOTTOM)).extract_text() or ""
    print("=== HEADER ===")
    print(header)
    print()
    
    # First 2 pages layout text
    for i in range(min(2, len(pdf.pages))):
        page = pdf.pages[i]
        text = extract_page_layout(page)
        print(f"=== PAGE {i} BODY (first 3000 chars) ===")
        print(text[:3000])
        print()

