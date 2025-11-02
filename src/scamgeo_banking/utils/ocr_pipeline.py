"""
ocr_pipeline.py
- run OCR on all images in a folder, extract text, save CSV with filename and extracted text
"""
import os, sys, csv
from PIL import Image
import pytesseract

if len(sys.argv)<2:
    print("Usage: python ocr_pipeline.py images_folder")
    sys.exit(1)

img_dir = sys.argv[1]
out_csv = "ocr_results.csv"
rows=[]
for fname in os.listdir(img_dir):
    if not fname.lower().endswith((".png",".jpg",".jpeg",".webp")):
        continue
    path = os.path.join(img_dir,fname)
    try:
        txt = pytesseract.image_to_string(Image.open(path), lang='eng+fra+deu+pol')
    except Exception as e:
        txt = ""
    rows.append((fname, txt.strip()[:5000]))
# write CSV
with open(out_csv,"w",newline='',encoding="utf-8") as cf:
    writer = csv.writer(cf)
    writer.writerow(["filename","text_snippet"])
    for r in rows:
        writer.writerow(r)
print("OCR done ->", out_csv)




