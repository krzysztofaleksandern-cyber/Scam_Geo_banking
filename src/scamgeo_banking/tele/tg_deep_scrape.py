#!/usr/bin/env python3
# tg_deep_scrape.py â€” gÅ‚Ä™boki scraping wiadomoÅ›ci z kanaÅ‚Ã³w TG + ekstrakcja URL/IBAN/krypto
import os, re, json, asyncio
from pathlib import Path
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import ChannelPrivateError, FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError
from telethon.tl.functions.channels import JoinChannelRequest

OUTDIR = Path("scam_hunter_out")
OUTDIR.mkdir(exist_ok=True)

# ReguÅ‚y ekstrakcji
URL_RE   = re.compile(r'https?://[^\s<>"\)\]]+')
IBAN_RE  = re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b')
BTC_RE   = re.compile(r'\b(?:bc1[a-z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b')
ETH_RE   = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
TRC20_RE = re.compile(r'\bT[1-9A-HJ-NP-Za-km-z]{33}\b')  # USDT (TRON)

def load_config():
    with open("config.json","r",encoding="utf-8") as f:
        cfg = json.load(f)
    tg = cfg["telegram"]
    seeds = cfg.get("seeds", [])
    return tg["api_id"], tg["api_hash"], tg.get("session_name","scamhunter.session"), seeds

async def get_or_join(client, handle):
    """
    PrÃ³buje pobraÄ‡ encjÄ™ po username.
    JeÅ›li nie jesteÅ› w kanale i jest publiczny â€” sprÃ³buje doÅ‚Ä…czyÄ‡.
    Zwraca (entity, joined_bool)
    """
    try:
        entity = await client.get_entity(handle)
        return entity, False
    except (UsernameInvalidError, UsernameNotOccupiedError):
        return None, False
    except ChannelPrivateError:
        # prywatny â€“ nie wejdziemy bez zaproszenia
        return None, False
    except Exception:
        # sprÃ³buj jawnie join
        try:
            entity = await client(JoinChannelRequest(handle))
            return entity, True
        except Exception:
            return None, False

def extract_from_text(text):
    urls   = URL_RE.findall(text) if text else []
    ibans  = IBAN_RE.findall(text) if text else []
    btc    = BTC_RE.findall(text) if text else []
    eth    = ETH_RE.findall(text) if text else []
    trc20  = TRC20_RE.findall(text) if text else []
    return urls, ibans, btc, eth, trc20

async def scrape_channel(client, handle, limit=500):
    """
    Pobiera ostatnie 'limit' wiadomoÅ›ci, wyciÄ…ga wzorce,
    zwraca strukturÄ™ z wynikami.
    """
    result = {
        "handle": handle,
        "joined": False,
        "ok": False,
        "title": None,
        "about": None,
        "errors": [],
        "urls": [],
        "ibans": [],
        "btc": [],
        "eth": [],
        "trc20": [],
        "samples": []  # krÃ³tkie prÃ³bki wiadomoÅ›ci z linkami
    }
    entity, joined = await get_or_join(client, handle)
    if not entity:
        result["errors"].append("entity_not_accessible")
        return result
    result["joined"] = joined
    try:
        # title/about gdy dostÄ™pne
        if hasattr(entity, 'title'):
            result["title"] = entity.title
        if hasattr(entity, 'about'):
            result["about"] = entity.about

        async for msg in client.iter_messages(entity, limit=limit):
            text = None
            if msg.raw_text:
                text = msg.raw_text
            elif msg.message:
                text = msg.message
            if not text:
                continue

            urls, ibans, btc, eth, trc20 = extract_from_text(text)
            if urls or ibans or btc or eth or trc20:
                result["urls"].extend(urls)
                result["ibans"].extend(ibans)
                result["btc"].extend(btc)
                result["eth"].extend(eth)
                result["trc20"].extend(trc20)
                # zapisz prÃ³bkÄ™ (skrÃ³conÄ…) do Å‚atwego przeglÄ…du
                snippet = text.replace("\n"," ")[:280]
                result["samples"].append({"id": msg.id, "date": str(msg.date), "text": snippet})

        # deduplikacja
        result["urls"]  = sorted(set(result["urls"]))
        result["ibans"] = sorted(set(result["ibans"]))
        result["btc"]   = sorted(set(result["btc"]))
        result["eth"]   = sorted(set(result["eth"]))
        result["trc20"] = sorted(set(result["trc20"]))
        result["ok"] = True
        return result
    except FloodWaitError as e:
        result["errors"].append(f"flood_wait:{e.seconds}s")
        return result
    except ChannelPrivateError:
        result["errors"].append("private_channel")
        return result
    except Exception as e:
        result["errors"].append(repr(e))
        return result

async def main_async():
    api_id, api_hash, session_name, seeds = load_config()
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print(f"Signed in as: {await client.get_me()}")

    handles = [s.lstrip("@") for s in seeds if isinstance(s, str) and len(s) >= 5]
    full = []
    for h in handles:
        print(f"[SCRAPE] {h}")
        data = await scrape_channel(client, h, limit=700)
        full.append(data)

    # zapis raportu
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_json = OUTDIR / f"deep_report_{ts}.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"channels": full}, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved: {out_json}")

    # przygotuj domeny do whois
    domains = set()
    for ch in full:
        for u in ch.get("urls", []):
            try:
                # wyciÄ…gnij netloc
                from urllib.parse import urlparse
                p = urlparse(u)
                if p.netloc:
                    domains.add(p.netloc.lower())
            except:
                pass
    if domains:
        dom_txt = OUTDIR / "domains_to_check.txt"
        with open(dom_txt, "a", encoding="utf-8") as f:
            for d in sorted(domains):
                f.write(d + "\n")
        print(f"[OK] Appended {len(domains)} domains -> {dom_txt}")

if __name__ == "__main__":
    asyncio.run(main_async())




