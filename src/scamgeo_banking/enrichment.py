from __future__ import annotations
import csv
import hashlib
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set
from urllib.parse import urlparse

import requests


URL_RE = re.compile(r"https?://[^\s,]+", re.I)


def _read_urls_from_csv(path: Path) -> Set[str]:
    urls: Set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        # szukamy kolumny "url" lub próbujemy wyciągać z "title"/"source"
        for row in rd:
            if "url" in row and row["url"]:
                urls.add(row["url"])
            else:
                for col in ("title", "source"):
                    if col in row and row[col]:
                        for m in URL_RE.findall(row[col]):
                            urls.add(m)
    return urls


def _domain_from_url(u: str) -> str:
    try:
        host = urlparse(u).hostname or ""
        return host.lower()
    except Exception:
        return ""


def _vt_lookup(u: str, api_key: str, timeout: float = 8.0) -> Dict[str, str]:
    """
    Minimalne VT: sprawdzamy url/ analiza reputacji przez v3 (jeśli jest klucz).
    Jeśli brak klucza/limit/exception -> zwracamy stub ze skrótem SHA256.
    """
    if not api_key:
        return {"vt_status": "no_key", "vt_votes": "", "vt_link": ""}
    try:
        headers = {"x-apikey": api_key}
        # VT wymaga najpierw submit/lookup – tu robimy prosty GET do „urls” (hashowane wg VT)
        # Hash dla endpointu /urls/{id} to url_id = base64_urlsafe(url). Ale uprośćmy:
        # użyjemy /search jako fallback:
        r = requests.get(
            "https://www.virustotal.com/api/v3/search",
            params={"query": u},
            headers=headers,
            timeout=timeout,
        )
        if r.status_code == 200:
            data = r.json()
            count = data.get("meta", {}).get("count", "")
            link = f"https://www.virustotal.com/gui/search/{u}"
            return {"vt_status": "ok", "vt_votes": str(count), "vt_link": link}
        else:
            return {"vt_status": f"err_{r.status_code}", "vt_votes": "", "vt_link": ""}
    except Exception as e:
        return {"vt_status": f"exc_{type(e).__name__}", "vt_votes": "", "vt_link": ""}


def _otx_lookup(domain: str, api_key: str, timeout: float = 8.0) -> Dict[str, str]:
    if not api_key:
        return {"otx_status": "no_key", "otx_pulses": "", "otx_link": ""}
    try:
        headers = {"X-OTX-API-KEY": api_key}
        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general"
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            pulses = len(data.get("pulse_info", {}).get("pulses", []))
            link = f"https://otx.alienvault.com/indicator/domain/{domain}"
            return {"otx_status": "ok", "otx_pulses": str(pulses), "otx_link": link}
        else:
            return {"otx_status": f"err_{r.status_code}", "otx_pulses": "", "otx_link": ""}
    except Exception as e:
        return {"otx_status": f"exc_{type(e).__name__}", "otx_pulses": "", "otx_link": ""}


def enrich_reputation(inputs: Iterable[Path], out_dir: Path, *, vt_key: str | None, otx_key: str | None) -> Path:
    """
    inputs: list CSV z kolumną `url`
    wyjście: out/web_reputation.csv z kolumnami:
      url, domain, vt_status, vt_votes, vt_link, otx_status, otx_pulses, otx_link, sha256
    """
    all_urls: Set[str] = set()
    for p in inputs:
        if p.exists():
            all_urls |= _read_urls_from_csv(p)

    rows: List[List[str]] = [
        ["url", "domain", "vt_status", "vt_votes", "vt_link", "otx_status", "otx_pulses", "otx_link", "sha256"]
    ]

    for u in sorted(all_urls):
        d = _domain_from_url(u)
        sha = hashlib.sha256(u.encode("utf-8")).hexdigest()
        vt = _vt_lookup(u, vt_key or "")
        otx = _otx_lookup(d, otx_key or "") if d else {"otx_status": "", "otx_pulses": "", "otx_link": ""}
        rows.append([
            u,
            d,
            vt.get("vt_status", ""),
            vt.get("vt_votes", ""),
            vt.get("vt_link", ""),
            otx.get("otx_status", ""),
            otx.get("otx_pulses", ""),
            otx.get("otx_link", ""),
            sha,
        ])

    out = out_dir / "web_reputation.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerows(rows)
    return out
