from __future__ import annotations
from typing import Iterable, List, Dict
from pathlib import Path
import csv
from ..platforms.youtube import fetch_channel_recent
from ..platforms.tiktok import fetch_profile_recent
from ..platforms.facebook import fetch_page_recent
from ..platforms.common_fetch import WebItem
from ..scoring.banking import score_text


SUPPORTED = {"youtube", "tiktok", "facebook"}


def scan_targets(targets: Iterable[str], out_dir: Path) -> List[Dict]:
out_dir.mkdir(parents=True, exist_ok=True)
rows: List[Dict] = []
for t in targets:
t = t.strip()
if not t:
continue
if t.startswith("yt:"):
ch = t.split(":",1)[1]
items = fetch_channel_recent(ch, limit=10)
elif t.startswith("tt:"):
handle = t.split(":",1)[1].lstrip("@")
items = fetch_profile_recent(handle, limit=10)
elif t.startswith("fb:"):
page = t.split(":",1)[1]
items = fetch_page_recent(page, limit=10)
else:
# raw URL: try best effort classification by hostname
if "youtube.com/channel/" in t or "feeds/videos.xml?channel_id=" in t:
ch = t.rsplit("/",1)[-1].split("=")[-1]
items = fetch_channel_recent(ch, limit=10)
else:
items = []
for it in items:
sc = score_text(it.text or "", it.url)
rows.append({
"platform": it.platform,
"source": it.source,
"url": it.url,
"title": it.title or "",
"label": sc["label"],
"score": sc["score"],
"hits": sc["hits"],
})
# write csv
out_csv = out_dir / "webscan_scored.csv"
with out_csv.open("w", newline="", encoding="utf-8") as f:
w = csv.DictWriter(f, fieldnames=["platform","source","url","title","label","score","hits"])
w.writeheader(); w.writerows(rows)
return rows