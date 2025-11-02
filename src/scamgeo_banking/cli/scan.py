# src/scamgeo_banking/cli/scan.py
from __future__ import annotations

from pathlib import Path
from typing import List, Dict
import csv

# ─── Małe utilsy ────────────────────────────────────────────────────────────────

def score_label(score: int) -> str:
    """Mapowanie score → etykieta."""
    if score >= 60:
        return "scam"
    if score >= 30:
        return "watch"
    return "ok"

def write_csv(path: Path, rows: List[Dict]) -> None:
    """Zapis listy dict do CSV z nagłówkiem (z kluczy pierwszego wiersza)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        # minimalny nagłówek zgodny z resztą narzędzia
        hdr = ["platform", "source", "url", "title", "label", "score", "hits"]
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(hdr)
        return

    hdr = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader()
        w.writerows(rows)

# ─── Skanery (stub/feeds) ──────────────────────────────────────────────────────

def scan_web_targets(targets: List[str], out_dir: Path) -> List[Dict]:
    """
    Stub skanera YT/TT/FB. Dla YT tworzy feed URL, dla TT/FB generuje “udawane” rekordy.
    Zwraca listę wierszy (dict) i NIE zapisuje nic sam – zapis robi write_csv().
    """
    rows: List[Dict] = []
    for t in targets:
        t = t.strip()
        if not t:
            continue
        if t.startswith("yt:"):
            chan = t.split(":", 1)[1]
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id={chan}"
            rows.append({
                "platform": "youtube",
                "source": t,
                "url": url,
                "title": "Google for Developers",  # placeholder
                "label": "ok",
                "score": 0,
                "hits": 0,
            })
        elif t.startswith("tt:"):
            handle = t.split(":", 1)[1]
            url = f"https://www.tiktok.com/@{handle}"
            rows.append({
                "platform": "tiktok",
                "source": t,
                "url": url,
                "title": f"tt:{t}",
                "label": "ok",
                "score": 0,
                "hits": 0,
            })
        elif t.startswith("fb:"):
            page = t.split(":", 1)[1]
            url = f"https://www.facebook.com/{page}"
            rows.append({
                "platform": "facebook",
                "source": t,
                "url": url,
                "title": page,
                "label": "ok",
                "score": 0,
                "hits": 0,
            })
        else:
            # Nieznany prefiks – potraktuj jako watch
            rows.append({
                "platform": "unknown",
                "source": t,
                "url": t,
                "title": t,
                "label": "watch",
                "score": 30,
                "hits": 1,
            })
    return rows

def sweep_keywords(queries: List[str], out_dir: Path) -> List[Dict]:
    """
    Stub “wyszukiwarki”: zwraca po jednym rekordzie na frazę + prosty scoring heurystyczny.
    """
    rows: List[Dict] = []
    for q in queries:
        qn = q.strip()
        if not qn:
            continue

        url_q = qn.replace(" ", "+")
        url = f"https://www.google.com/search?q={url_q}"

        # heurystyka:
        ql = qn.lower()
        score = 0
        hits  = 0
        if "pewny zysk" in ql or "sure profit" in ql:
            score += 60; hits += 1
        if "binance" in ql and "bonus" in ql:
            score = max(score, 40); hits += 1
        if "t.me/" in ql or "whatsapp" in ql:
            score = max(score, 50 if "dopłata" in ql or "dopłata do konta" in ql else 30); hits += 1

        label = score_label(score)

        rows.append({
            "platform": "search",
            "source": qn,
            "url": url,
            "title": qn,
            "label": label,
            "score": score,
            "hits": hits,
        })
    return rows

def scan_ads(targets: List[str], out_dir: Path) -> List[Dict]:
    """
    Stub inspektora reklam: zwraca po jednym “ad:*” rek. na target.
    """
    rows: List[Dict] = []
    for t in targets:
        t = t.strip()
        if not t:
            continue
        rows.append({
            "platform": "ads",
            "source": t,
            "url": f"https://ads.example.org/inspect?src={t}",
            "title": f"ad:{t}",
            "label": "ok",
            "score": 0,
            "hits": 0,
        })
    return rows
