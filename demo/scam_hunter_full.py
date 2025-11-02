"""
scam_hunter_full.py
- main orchestrator: web crawl (public), Telegram public entities (Telethon),
  extract IBAN/URLs/TG handles, WHOIS/ASN, optional OCR hook, save JSON/CSV.
- Configure via config.json (copy config.example.json)
"""
import os, json, time, re, csv
from urllib.parse import urlparse
import tldextract
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from telethon import TelegramClient
import asyncio

# helpers
IBAN_RE = re.compile(r'\b[A-Z]{2}[0-9]{2}[ ]?[0-9A-Z]{10,30}\b')
TG_LINK_RE = re.compile(r'(?:t\.me\/|telegram\.me\/)([A-Za-z0-9_]+)')
URL_RE = re.compile(r'https?://[^\s"<>]+')

# load config
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
OUTDIR = cfg.get("outdir", "scam_hunter_out")
os.makedirs(OUTDIR, exist_ok=True)

# basic web crawl (seed pages) - finds t.me links and urls
def crawl_page_for_links(url):
    found = set()
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"scam-hunter/1.0"})
        if r.status_code != 200:
            return found
        text = r.text
        for m in TG_LINK_RE.finditer(text):
            found.add(m.group(1))
        for u in URL_RE.findall(text):
            found.add(u)
    except Exception as e:
        print("crawl error", url, e)
    return found

# telegram fetch
async def fetch_telegram_info(seeds):
    tg_cfg = cfg["telegram"]
    client = TelegramClient(tg_cfg["session_name"], tg_cfg["api_id"], tg_cfg["api_hash"])
    results = {}
    async with client:
        for nick in seeds:
            try:
                ent = await client.get_entity(nick)
            except Exception as e:
                results[nick] = {"error":"not found or private", "exc": str(e)}
                continue
            info = {
                "username": getattr(ent, "username", None),
                "title": getattr(ent, "title", None),
                "id": getattr(ent, "id", None),
                "about": None,
                "links_found": []
            }
            # try about/description (if available)
            try:
                full = await client.get_entity(ent)
                about = getattr(full, "about", None)
                if about:
                    info["about"] = about
                    for u in URL_RE.findall(about):
                        info["links_found"].append(u)
            except Exception:
                pass
            results[nick] = info
            time.sleep(1)  # polite
    return results

# whois/domain helper
def extract_domain(u):
    try:
        p = urlparse(u)
        ext = tldextract.extract(p.netloc)
        if ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        return p.netloc
    except:
        return None

# main
def main():
    seeds = set(cfg.get("seeds", []))
    # web seeds crawl
    for w in cfg.get("web_seeds", []):
        found = crawl_page_for_links(w)
        for f in found:
            if '/' not in f and not f.startswith('http'):
                seeds.add(f)
            else:
                # url
                domain = extract_domain(f)
                if domain:
                    seeds.add(f)
    seeds = list(seeds)
    with open(os.path.join(OUTDIR, "seeds.json"), "w", encoding="utf-8") as f:
        json.dump({"seeds": seeds}, f, ensure_ascii=False, indent=2)
    # telegram
    tg_results = asyncio.run(fetch_telegram_info(seeds))
    with open(os.path.join(OUTDIR, "tg_results.json"), "w", encoding="utf-8") as f:
        json.dump(tg_results, f, ensure_ascii=False, indent=2)
    # extract ibans/urls
    ibans, urls = set(), set()
    for k,v in tg_results.items():
        if isinstance(v, dict):
            about = v.get("about") or ""
            for ib in IBAN_RE.findall(about):
                ibans.add(ib.replace(" ", ""))
            for u in URL_RE.findall(about):
                urls.add(u)
    # do domain extraction + minimal whois via python-whois (separate script recommended)
    domains = {}
    for u in list(urls):
        d = extract_domain(u)
        if d and d not in domains:
            domains[d] = {"domain": d}
    out = {
        "tg_results": tg_results,
        "found_ibans": list(ibans),
        "found_urls": list(urls),
        "domains": domains
    }
    with open(os.path.join(OUTDIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    # CSV summary
    with open(os.path.join(OUTDIR, "channels.csv"), "w", newline='', encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(["username","title","id","about","links_found"])
        for k,v in tg_results.items():
            writer.writerow([v.get("username") or k, v.get("title"), v.get("id"), (v.get("about") or "")[:300].replace("\n"," "), ",".join(v.get("links_found") or [])])
    print("Done. Outputs in", OUTDIR)

if __name__ == "__main__":
    main()
