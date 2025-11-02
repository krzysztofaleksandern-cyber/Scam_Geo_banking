#!/usr/bin/env python3
# extract_seeds_from_html.py
import re, os, json, sys
from bs4 import BeautifulSoup

HTML_FN = sys.argv[1] if len(sys.argv) > 1 else "messages.html"
OUTDIR = "scam_hunter_out"
os.makedirs(OUTDIR, exist_ok=True)

TG_LINK_RE = re.compile(r'(?:t\.me|telegram\.me)/([A-Za-z0-9_]+)/?')
URL_RE = re.compile(r'https?://[^\s"<>]+')

def load_html(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def extract(text):
    tg_handles = set()
    for m in TG_LINK_RE.finditer(text):
        handle = m.group(1)
        if handle:
            tg_handles.add(handle)
    urls = set(URL_RE.findall(text))
    return sorted(tg_handles), sorted(urls)

def append_seeds_to_config(handles):
    cfg_path = "config.json"
    if not os.path.exists(cfg_path):
        print("config.json not found â€” skipping config update")
        return
    cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
    seeds = set(cfg.get("seeds", []))
    before = len(seeds)
    seeds.update(handles)
    cfg["seeds"] = sorted(seeds)
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"Config seeds updated: {before} -> {len(seeds)}")

def main():
    text = load_html(HTML_FN)
    try:
        soup = BeautifulSoup(text, "lxml")
        text = soup.get_text(" ")
    except Exception:
        pass

    tg_handles, urls = extract(text)

    with open(os.path.join(OUTDIR, "html_seeds.json"), "w", encoding="utf-8") as f:
        json.dump({"tg_handles": tg_handles}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(OUTDIR, "html_urls.txt"), "w", encoding="utf-8") as f:
        for u in urls:
            f.write(u + "\n")

    append_seeds_to_config(tg_handles)

    print(f"Found TG handles: {len(tg_handles)}, URLs: {len(urls)}")
    print(f"Outputs: {OUTDIR}\\html_seeds.json, {OUTDIR}\\html_urls.txt")

if __name__ == "__main__":
    main()




