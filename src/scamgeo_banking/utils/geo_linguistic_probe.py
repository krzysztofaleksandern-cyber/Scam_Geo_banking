# zapisz ten plik i uruchom: python -m pip install beautifulsoup4 langdetect
# potem: python geo_linguistic_probe.py messages.html
import sys, re, json
from bs4 import BeautifulSoup
from langdetect import detect, DetectorFactory
from datetime import datetime
DetectorFactory.seed = 0

fn = sys.argv[1]
with open(fn,"r",encoding="utf-8",errors="ignore") as f:
    s = BeautifulSoup(f,"lxml")

msgs=[]
for el in s.find_all(class_=re.compile(r"(message|msg|bubble|row)")):
    # author
    a=el.find(class_=re.compile(r"(from_name|name|from)"))
    author=a.get_text(strip=True) if a else ""
    # time
    d=el.find(class_=re.compile(r"(date|time|details)"))
    dt = d['title'] if d and d.has_attr('title') else (d.get_text(strip=True) if d else "")
    # text
    t=el.find(class_=re.compile(r"(text|body|bubble)"))
    txt = t.get_text(" ",strip=True) if t else el.get_text(" ",strip=True)
    msgs.append({"author":author,"dt":dt,"text":txt})

# normalize, detect messages for Laura and K N, compute reply delays and language distribution
laura=[m for m in msgs if "laura" in m['author'].lower() or "polat" in m['author'].lower()]
kn=[m for m in msgs if m['author'].strip().upper().startswith("K N") or m['author'].strip()=="K N"]
for m in laura+kn:
    try:
        m['lang']=detect(m['text'])
    except:
        m['lang']="unk"
print("Laura msgs:",len(laura),"K N msgs:",len(kn))
lc={}
for m in laura:
    lc[m['lang']]=lc.get(m['lang'],0)+1
print("Laura lang dist:",lc)

# simple reaction time
from datetime import datetime
def parse_dt(s):
    for fmt in ("%d.%m.%Y %H:%M","%H:%M","%d.%m.%Y %H:%M:%S"):
        try:
            return datetime.strptime(s,fmt)
        except:
            continue
    return None

deltas=[]
for k in kn:
    pk=parse_dt(k['dt'])
    if not pk: continue
    later=[l for l in laura if parse_dt(l['dt']) and parse_dt(l['dt'])>=pk]
    if later:
        deltas.append((parse_dt(later[0]['dt'])-pk).total_seconds())
if deltas:
    import statistics
    print("Median reply (s):",statistics.median(deltas),"Mean(s):",statistics.mean(deltas))
else:
    print("No reply deltas computed")




