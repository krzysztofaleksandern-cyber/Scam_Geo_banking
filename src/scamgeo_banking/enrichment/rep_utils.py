#!/usr/bin/env python3
# domains_refresh.py â€” wyciÄ…ga domeny z deep_report_* i html_urls.txt
import json, glob, os
from urllib.parse import urlparse

OUT = "scam_hunter_out/domains_to_check.txt"

def add_domain(s, acc):
    s = s.strip()
    if not s: return
    # jeÅ›li peÅ‚ny URL â†’ wytnij domenÄ™
    if "://" in s:
        try:
            netloc = urlparse(s).netloc.lower()
            if netloc:
                acc.add(netloc)
                return
        except:
            pass
    # jeÅ›li juÅ¼ domena
    if "/" not in s and " " not in s:
        acc.add(s.lower())

def main():
    acc = set()

    # 1) ostatni deep_report_*.json
    reps = sorted(glob.glob("scam_hunter_out/deep_report_*.json"))
    if reps:
        p = reps[-1]
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        for ch in data.get("channels", []):
            for u in ch.get("urls", []):
                add_domain(u, acc)

    # 2) html_urls.txt (jeÅ›li istnieje)
    if os.path.exists("scam_hunter_out/html_urls.txt"):
        for line in open("scam_hunter_out/html_urls.txt", "r", encoding="utf-8"):
            add_domain(line, acc)

    # 3) dorzuÄ‡ istniejÄ…ce (oczyszczone)
    if os.path.exists(OUT):
        for line in open(OUT, "r", encoding="utf-8"):
            add_domain(line, acc)

    os.makedirs("scam_hunter_out", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for d in sorted(acc):
            f.write(d + "\n")

    print(f"Zapisano {len(acc)} domen -> {OUT}")

if __name__ == "__main__":
    main()




