# scam_hunter_basic.py
# Python 3.10+ recommended
# pip install telethon requests beautifulsoup4 tldextract python-whois langdetect pandas

import re, os, json, csv, time
from telethon import TelegramClient
import requests
from bs4 import BeautifulSoup
import tldextract
import whois
from langdetect import detect, LangDetectException
from urllib.parse import urljoin, urlparse
from collections import defaultdict

# ---------- CONFIG ----------
API_ID = <YOUR_API_ID>      # replace
API_HASH = "<YOUR_API_HASH>"# replace
SESSION_NAME = "scamhunter.session"
OUTDIR = "scam_hunter_out"
os.makedirs(OUTDIR, exist_ok=True)

# starter seeds: nicki / linki które chcesz śledzić
SEEDS = [
    "EURGowin", "Rafik3546", "qwe12345678LLL"  # przykłady; dodaj swoje
]
# web seed pages to crawl (optional)
WEB_SEEDS = [
    "https://pastebin.com", # example, will be used to search t.me links
]

# regex
TG_LINK_RE = re.compile(r'(?:t\.me\/|telegram\.me\/)([A-Za-z0-9_]+)')
URL_RE = re.compile(r'https?://[^\s"<>]+')
IBAN_RE = re.compile(r'\b[A-Z]{2}[0-9]{2}[ ]?[0-9A-Z]{10,30}\b')

# ---------- HELPERS ----------
def safe_detect_lang(s):
    try:
        return detect(s)
    except LangDetectException:
        return None

def whois_lookup(domain):
    try:
        w = whois.whois(domain)
        return {
            "domain": domain,
            "whois": {
                "registrar": w.registrar,
                "creation_date": str(w.creation_date),
                "country": w.country,
                "emails": w.emails
            }
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)}

def crawl_page_for_tg(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"scam-hunter/1.0"})
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        found = set()
        for a in soup.find_all("a", href=True):
            m = TG_LINK_RE.search(a['href'])
            if m:
                found.add(m.group(1))
        # also look in text
        for m in TG_LINK_RE.finditer(r.text):
            found.add(m.group(1))
        return list(found)
    except Exception as e:
        return []

# ---------- TELEGRAM COLLECT ----------
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def fetch_telegram_info(seeds):
    results = {}
    async with client:
        for nick in seeds:
            try:
                entity = await client.get_entity(nick)
            except Exception as e:
                results[nick] = {"error":"not found or private", "exc": str(e)}
                continue
            info = {
                "username": getattr(entity, "username", None),
                "title": getattr(entity, "title", None),
                "id": getattr(entity, "id", None),
                "members": getattr(entity, "participants_count", None),
                "about": None,
                "links_found": [],
            }
            try:
                full = await client.get_entity(entity)
                # try to get about/description if channel
                if hasattr(full, "about"):
                    info["about"] = full.about
                    # extract t.me links and urls from about
                    for u in URL_RE.findall(full.about or ""):
                        info["links_found"].append(u)
            except Exception as e:
                pass
            results[nick] = info
            time.sleep(1)
    return results

# ---------- MAIN ----------
def main():
    # 1) web crawl seeds -> find tg handles
    discovered = set(SEEDS)
    for seedurl in WEB_SEEDS:
        tgs = crawl_page_for_tg(seedurl)
        for t in tgs:
            discovered.add(t)
    # Save seed list
    with open(os.path.join(OUTDIR, "seeds.json"), "w", encoding="utf-8") as f:
        json.dump({"seeds": list(discovered)}, f, ensure_ascii=False, indent=2)

    # 2) fetch from Telegram (public info)
    import asyncio
    tg_results = asyncio.run(fetch_telegram_info(list(discovered)))
    with open(os.path.join(OUTDIR, "tg_results.json"), "w", encoding="utf-8") as f:
        json.dump(tg_results, f, ensure_ascii=False, indent=2)

    # 3) Extract IBANs and URLs from 'about' fields
    ibans = set()
    urls = set()
    for k,v in tg_results.items():
        if isinstance(v, dict):
            about = v.get("about") or ""
            for ib in IBAN_RE.findall(about):
                ibans.add(ib.replace(" ",""))
            for u in URL_RE.findall(about):
                urls.add(u)

    # 4) WHOIS for found domains
    domain_info = {}
    for u in list(urls):
        parsed = urlparse(u)
        ext = tldextract.extract(parsed.netloc)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else parsed.netloc
        if domain not in domain_info:
            domain_info[domain] = whois_lookup(domain)
            time.sleep(1)

    # save
    out = {
        "tg_results": tg_results,
        "found_ibans": list(ibans),
        "found_urls": list(urls),
        "domains": domain_info
    }
    with open(os.path.join(OUTDIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # write CSV summary
    with open(os.path.join(OUTDIR, "channels.csv"), "w", newline='', encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(["username","title","id","members","about","links"])
        for k,v in tg_results.items():
            if isinstance(v, dict):
                writer.writerow([v.get("username") or k, v.get("title"), v.get("id"), v.get("members"), (v.get("about") or "")[:200].replace("\n"," "), ",".join(v.get("links_found") or [])])

    print("Done. Outputs in", OUTDIR)

if __name__ == "__main__":
    main()
