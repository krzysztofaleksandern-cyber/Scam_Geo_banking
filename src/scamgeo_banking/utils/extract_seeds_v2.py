#!/usr/bin/env python3
# extract_seeds_v2.py
# Z: messages.html + channels.csv + @wzmianki + t.me/(handle|joinchat|+code) + manual_seeds.txt
import re, os, sys, json, csv
from bs4 import BeautifulSoup

HTML = "messages.html"
CHANNELS_CSV = "channels.csv"                 # jeÅ›li jest
MANUAL_TXT = "manual_seeds.txt"               # podaj tam dodatkowe seedy w kaÅ¼dej linii
OUTDIR = "scam_hunter_out"
os.makedirs(OUTDIR, exist_ok=True)

# Wzorce
TG_HANDLE = re.compile(r'(?:^|[^a-zA-Z0-9_])@([A-Za-z0-9_]{5,})')  # @username (>=5)
TG_URL_HANDLE = re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{5,})(?:/[\d_]+)?')
TG_URL_JOIN = re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/(?:joinchat/\w+|\+[A-Za-z0-9_-]{10,})')
URL_RE = re.compile(r'https?://[^\s"<>]+')

def read_text(path):
    try:
        return open(path, "r", encoding="utf-8", errors="ignore").read()
    except:
        return ""

def extract_from_html(html_text):
    handles, joinlinks, urls = set(), set(), set()
    try:
        soup = BeautifulSoup(html_text, "lxml")
        text = soup.get_text(" ")
        html_text = text if text else html_text
    except Exception:
        pass

    # @wzmianki
    for m in TG_HANDLE.finditer(html_text):
        handles.add(m.group(1))

    # t.me/handle[/post]
    for m in TG_URL_HANDLE.finditer(html_text):
        handles.add(m.group(1))

    # zaproszenia joinchat / +kod
    for m in TG_URL_JOIN.finditer(html_text):
        joinlinks.add(m.group(0))

    # zwykÅ‚e URL-e (do WHOIS)
    for u in URL_RE.findall(html_text):
        urls.add(u)

    return handles, joinlinks, urls

def extract_from_channels_csv():
    h = set()
    if not os.path.exists(CHANNELS_CSV):
        return h
    with open(CHANNELS_CSV, "r", encoding="utf-8", errors="ignore") as f:
        r = csv.reader(f)
        header = next(r, [])
        for row in r:
            # sprÃ³buj kolumny: username / first cell
            for cell in row:
                if not cell: continue
                m = TG_URL_HANDLE.search(cell)
                if m: h.add(m.group(1))
                if re.fullmatch(r'[A-Za-z0-9_]{5,}', cell): h.add(cell)
    return h

def read_manual():
    h = set()
    if not os.path.exists(MANUAL_TXT):
        return h
    for line in open(MANUAL_TXT, "r", encoding="utf-8", errors="ignore"):
        s = line.strip()
        if not s: continue
        # przyjmij zarÃ³wno @handle jak i same handle
        if s.startswith("@"): s = s[1:]
        if re.fullmatch(r'[A-Za-z0-9_]{5,}', s):
            h.add(s)
    return h

def update_config(handles):
    path = "config.json"
    if not os.path.exists(path):
        print("config.json not found â€” skipping update")
        return 0,0
    cfg = json.load(open(path, "r", encoding="utf-8"))
    seeds = set(cfg.get("seeds", []))
    before = len(seeds)
    seeds |= handles
    cfg["seeds"] = sorted(seeds)
    json.dump(cfg, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return before, len(seeds)

def main():
    html_text = read_text(HTML)
    h1, joinlinks, urls = extract_from_html(html_text)
    h2 = extract_from_channels_csv()
    h3 = read_manual()
    all_handles = h1 | h2 | h3

    # zapisz poÅ›rednie wyniki
    with open(os.path.join(OUTDIR, "html_seeds.json"), "w", encoding="utf-8") as f:
        json.dump({"tg_handles": sorted(all_handles),
                   "join_links": sorted(joinlinks)}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(OUTDIR, "html_urls.txt"), "w", encoding="utf-8") as f:
        for u in sorted(urls):
            f.write(u + "\n")

    b, a = update_config(all_handles)
    print(f"Found: handles={len(all_handles)}, joinlinks={len(joinlinks)}, urls={len(urls)}")
    print(f"config.json seeds: {b} -> {a}")
    print(f"Outputs: {OUTDIR}\\html_seeds.json, {OUTDIR}\\html_urls.txt")

if __name__ == "__main__":
    main()




