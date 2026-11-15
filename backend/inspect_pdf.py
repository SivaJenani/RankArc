import pdfplumber

PDF_PATH = r'C:/Users/sivajenani/.gemini/antigravity/brain/bad96cca-a60e-435a-8018-df2563775815/.user_uploaded/media_1794492844207_18b4dd6a.pdf'

with pdfplumber.open(PDF_PATH) as pdf:
    page = pdf.pages[0]
    w, h = page.width, page.height
    print(f"Page size: {w} x {h}")
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    print(f"Total words on page 0: {len(words)}")
    for wo in words[:60]:
        print(f"  x0={wo['x0']:.1f} top={wo['top']:.1f} text={repr(wo['text'])}")
    
    print("\n--- Testing layout-aware extraction ---")
    # Try layout parameter
    try:
        layout_text = page.extract_text(layout=True)
        print("Layout text (first 2000 chars):")
        print(layout_text[:2000])
    except Exception as e:
        print(f"layout=True failed: {e}")

