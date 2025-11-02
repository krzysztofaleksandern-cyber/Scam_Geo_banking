# Telegram Country Inference â€“ MVP
# --------------------------------
# Cel: oszacowaÄ‡ KRAJ scammera na bazie danych z Telegrama.
# DziaÅ‚a w dwÃ³ch trybach:
#   (A) Offline â€“ analiza eksportu czatu z Telegram Desktop (JSON `result.json`).
#   (B) Live â€“ (opcjonalnie) pobranie publicznej historii wiadomoÅ›ci przez MTProto (Telethon).
#       Wymaga wÅ‚asnych kluczy API (my.telegram.org) i zalogowania numerem. JeÅ›li ich nie podasz,
#       skrypt dziaÅ‚a w trybie (A).
#
# Jak uÅ¼ywaÄ‡:
#   pip install langdetect python-dateutil emoji pycountry telethon tldextract
#   python tg_country_infer.py --export path\do\result.json
#   # lub (tryb LIVE â€“ opcjonalny):
#   set TG_API_ID=123456; set TG_API_HASH=abcd... (Windows PowerShell: $env:TG_API_ID="..."; $env:TG_API_HASH="...")
#   python tg_country_infer.py --username @someuser --limit 500
#
# Wynik: raport JSON + czytelny tekst z TOP krajami i dowodami.

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from dateutil import parser as dateparser
from langdetect import detect, DetectorFactory, LangDetectException
import tldextract

# Optional: only used for LIVE mode
try:
    from telethon import TelegramClient
    from telethon.tl.functions.users import GetFullUserRequest
    from telethon.tl.functions.messages import GetHistoryRequest
    TELETHON_OK = True
except Exception:
    TELETHON_OK = False

DetectorFactory.seed = 0  # reproducible langdetect

REGIONAL_FLAG_RE = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")  # emoji flags (regional indicators)
CURRENCY_SIGNALS = {
    "PLN": {"patterns": [r"\bPLN\b", r"zÅ‚", r"zl"], "countries": ["Poland"]},
    "EUR": {"patterns": [r"\bEUR\b", r"â‚¬"], "countries": ["Germany","Austria","Italy","Spain","France","Netherlands","Belgium","Portugal","Finland","Ireland","Estonia","Latvia","Lithuania","Slovakia","Slovenia","Greece","Cyprus","Luxembourg","Malta"]},
    "USD": {"patterns": [r"\bUSD\b", r"\$"], "countries": ["United States"]},
    "UAH": {"patterns": [r"\bUAH\b", r"Ð³Ñ€Ð½", r"uah"], "countries": ["Ukraine"]},
    "TRY": {"patterns": [r"\bTRY\b", r"â‚º"], "countries": ["Turkey"]},
    "RUB": {"patterns": [r"\bRUB\b", r"â‚½", r"Ñ€ÑƒÐ±"], "countries": ["Russia"]},
    "RON": {"patterns": [r"\bRON\b", r"lei", r"leu"], "countries": ["Romania"]},
    "HUF": {"patterns": [r"\bHUF\b", r"Ft\b"], "countries": ["Hungary"]},
    "CZK": {"patterns": [r"\bCZK\b", r"KÄ"], "countries": ["Czechia"]},
}

LANG_TO_COUNTRIES = {
    "pl": ["Poland"],
    "de": ["Germany","Austria","Switzerland"],
    "en": ["United States","United Kingdom","Ireland","Canada","Australia","New Zealand"],
    "ru": ["Russia","Belarus","Kazakhstan"],
    "uk": ["Ukraine"],
    "tr": ["Turkey"],
    "ro": ["Romania"],
    "hu": ["Hungary"],
    "cs": ["Czechia"],
    "sk": ["Slovakia"],
    "fr": ["France","Belgium","Switzerland","Canada"],
    "it": ["Italy"],
    "es": ["Spain","Mexico","Argentina","Colombia","Peru","Chile"]
}

UTC_OFFSETS = list(range(-12, 15))  # plausible UTC offsets

AWAKE_WINDOWS = [
    (8, 12),   # morning active
    (12, 14),  # lunch
    (18, 23),  # evening peak
]

TLD_COUNTRY_HINTS = {
    "pl": "Poland",
    "de": "Germany",
    "at": "Austria",
    "ch": "Switzerland",
    "cz": "Czechia",
    "sk": "Slovakia",
    "ro": "Romania",
    "hu": "Hungary",
    "ru": "Russia",
    "ua": "Ukraine",
    "tr": "Turkey",
    "it": "Italy",
    "fr": "France",
    "es": "Spain",
}


def detect_language(text: str) -> Optional[str]:
    try:
        return detect(text)
    except LangDetectException:
        return None


def parse_telegram_export(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Desktop export JSON has 'messages' list
    msgs = data.get("messages", [])
    records = []
    for m in msgs:
        if m.get("type") != "message":
            continue
        date = dateparser.parse(m.get("date"))
        txt = ""
        if isinstance(m.get("text"), list):
            # Telegram sometimes gives rich pieces; join text items
            for part in m.get("text"):
                if isinstance(part, str):
                    txt += part
                elif isinstance(part, dict):
                    txt += part.get("text", "")
        else:
            txt = m.get("text", "") or ""
        urls = []
        if isinstance(m.get("text"), list):
            for part in m.get("text"):
                if isinstance(part, dict) and part.get("type") == "link":
                    urls.append(part.get("text"))
        # Fallback: regex links
        urls += re.findall(r"https?://[^\s]+", txt)
        records.append({"date": date, "text": txt, "urls": list(set(urls))})
    return records


def infer_timezone_offset(dates: List[datetime]) -> Optional[int]:
    if not dates:
        return None
    # Convert to UTC hours
    hours = [d.astimezone(timezone.utc).hour for d in dates]
    # For each offset, shift hours and score awake windows
    best_offset, best_score = None, -1
    for off in UTC_OFFSETS:
        score = 0
        shifted = [((h + off) % 24) for h in hours]
        counter = Counter(shifted)
        for (a, b) in AWAKE_WINDOWS:
            for h in range(a, b + 1):
                score += counter.get(h % 24, 0)
        if score > best_score:
            best_score, best_offset = score, off
    return best_offset


def collect_language_signals(records: List[Dict[str,Any]]) -> Counter:
    c = Counter()
    for r in records:
        txt = (r.get("text") or "").strip()
        if not txt:
            continue
        lang = detect_language(txt)
        if lang:
            c[lang] += 1
    return c


def collect_currency_signals(records: List[Dict[str,Any]]) -> List[str]:
    hits = []
    for r in records:
        txt = r.get("text") or ""
        for code, meta in CURRENCY_SIGNALS.items():
            for patt in meta["patterns"]:
                if re.search(patt, txt, flags=re.IGNORECASE):
                    hits.extend(meta["countries"])
                    break
    return hits


def collect_tld_signals(records: List[Dict[str,Any]]) -> List[str]:
    countries = []
    for r in records:
        for url in r.get("urls", []):
            ext = tldextract.extract(url)
            tld = ext.suffix.split(".")[-1] if ext and ext.suffix else ""
            if tld in TLD_COUNTRY_HINTS:
                countries.append(TLD_COUNTRY_HINTS[tld])
    return countries


def collect_flag_emojis(records: List[Dict[str,Any]]) -> List[str]:
    # This detects presence of any country flags and maps to country via unicode regional indicators.
    # It's a weak heuristic but can help.
    flags = []
    for r in records:
        for m in REGIONAL_FLAG_RE.findall(r.get("text") or ""):
            flags.append(m)
    # Map of common flags (extend as needed)
    MAP = {
        "ðŸ‡µðŸ‡±": "Poland", "ðŸ‡©ðŸ‡ª": "Germany", "ðŸ‡¦ðŸ‡¹": "Austria", "ðŸ‡¨ðŸ‡­": "Switzerland",
        "ðŸ‡·ðŸ‡º": "Russia", "ðŸ‡ºðŸ‡¦": "Ukraine", "ðŸ‡¹ðŸ‡·": "Turkey", "ðŸ‡·ðŸ‡´": "Romania",
        "ðŸ‡­ðŸ‡º": "Hungary", "ðŸ‡¨ðŸ‡¿": "Czechia", "ðŸ‡¸ðŸ‡°": "Slovakia", "ðŸ‡®ðŸ‡¹": "Italy",
        "ðŸ‡«ðŸ‡·": "France", "ðŸ‡ªðŸ‡¸": "Spain", "ðŸ‡¬ðŸ‡§": "United Kingdom", "ðŸ‡ºðŸ‡¸": "United States",
    }
    countries = [MAP[f] for f in flags if f in MAP]
    return countries


def combine_signals(
    lang_counts: Counter,
    tz_offset: Optional[int],
    currencies: List[str],
    tld_countries: List[str],
    flag_countries: List[str]
) -> Tuple[List[Tuple[str,int]], List[Dict[str,Any]]]:
    score = Counter()
    evidence = []

    # Language â†’ Countries
    for lang, cnt in lang_counts.items():
        for country in LANG_TO_COUNTRIES.get(lang, []):
            pts = min(15, 3 * cnt)  # cap language influence
            score[country] += pts
            evidence.append({"country": country, "reason": f"Language {lang} ({cnt} msgs)", "points": pts})

    # Currency signals
    for c in currencies:
        score[c] += 12
        evidence.append({"country": c, "reason": "Currency mention", "points": 12})

    # TLD signals
    for c in tld_countries:
        score[c] += 8
        evidence.append({"country": c, "reason": "Country TLD in URLs", "points": 8})

    # Flag emojis
    for c in flag_countries:
        score[c] += 6
        evidence.append({"country": c, "reason": "Country flag emoji", "points": 6})

    # Timezone offset â†’ map to candidate countries (coarse)
    OFFSET_TO_COUNTRIES = {
        0: ["United Kingdom","Portugal","Ghana","Morocco"],
        1: ["Poland","Germany","Austria","Czechia","Slovakia","Hungary","Italy","France","Spain","Netherlands","Belgium","Switzerland"],
        2: ["Romania","Ukraine","Finland","Greece","Turkey"],
        3: ["Russia"],
        -5: ["United States"], -6: ["United States"], -7: ["United States"], -8: ["United States"],
        10: ["Australia"], 11: ["Australia"], -3: ["Argentina"], -4: ["Canada"],
    }
    if tz_offset in OFFSET_TO_COUNTRIES:
        for c in OFFSET_TO_COUNTRIES[tz_offset]:
            score[c] += 20
            evidence.append({"country": c, "reason": f"Active hours fit UTC{tz_offset:+d}", "points": 20})

    ranked = score.most_common()
    return ranked, evidence


# -------- LIVE MODE (optional) --------

def fetch_messages_live(username: str, limit: int = 300) -> List[Dict[str,Any]]:
    if not TELETHON_OK:
        raise RuntimeError("Telethon not installed; install 'telethon' to use live mode.")
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        raise RuntimeError("Set TG_API_ID and TG_API_HASH environment variables for live mode.")
    client = TelegramClient("tg_infer_session", int(api_id), api_hash)
    client.start()  # will prompt for phone/login on first run
    from telethon.tl.functions.messages import GetHistoryRequest
    from telethon.tl.types import InputPeerUser, InputPeerChannel

    entity = client.get_entity(username)
    hist = client(GetHistoryRequest(
        peer=entity,
        limit=limit,
        offset_date=None,
        offset_id=0,
        max_id=0,
        min_id=0,
        add_offset=0,
        hash=0
    ))
    records = []
    for m in hist.messages:
        if not getattr(m, 'message', None):
            continue
        date = m.date.replace(tzinfo=timezone.utc)
        txt = m.message or ""
        urls = re.findall(r"https?://[^\s]+", txt)
        records.append({"date": date, "text": txt, "urls": list(set(urls))})
    client.disconnect()
    return records


# -------- CLI --------

def main():
    ap = argparse.ArgumentParser(description="Infer likely country of a Telegram user/conversation")
    ap.add_argument("--export", help="Path to Telegram Desktop JSON export (result.json)")
    ap.add_argument("--username", help="@username or t.me/ link (LIVE mode)")
    ap.add_argument("--limit", type=int, default=400, help="Max messages to fetch in LIVE mode")
    args = ap.parse_args()

    records: List[Dict[str,Any]] = []

    if args.export:
        records = parse_telegram_export(args.export)
    elif args.username:
        records = fetch_messages_live(args.username, limit=args.limit)
    else:
        print("Provide --export or --username")
        return

    if not records:
        print(json.dumps({"error":"no_messages"}, ensure_ascii=False, indent=2))
        return

    # Signals
    dates = [r["date"] for r in records if isinstance(r.get("date"), datetime)]
    tz_offset = infer_timezone_offset(dates)
    lang_counts = collect_language_signals(records)
    curr_hits = collect_currency_signals(records)
    tld_hits = collect_tld_signals(records)
    flag_hits = collect_flag_emojis(records)

    ranked, evidence = combine_signals(lang_counts, tz_offset, curr_hits, tld_hits, flag_hits)

    # Confidence heuristic
    top_score = ranked[0][1] if ranked else 0
    sum_top3 = sum(s for _, s in ranked[:3])
    if top_score >= 40 and (top_score >= 0.6 * sum_top3):
        confidence = "high"
    elif top_score >= 25:
        confidence = "medium"
    else:
        confidence = "low"

    out = {
        "top_countries": [{"country": c, "score": s} for c, s in ranked[:5]],
        "confidence": confidence,
        "tz_offset": tz_offset,
        "languages": lang_counts,
        "currency_hits": curr_hits,
        "tld_country_hits": tld_hits,
        "flag_country_hits": flag_hits,
        "evidence": evidence[:50],
        "messages_analyzed": len(records)
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    main()




