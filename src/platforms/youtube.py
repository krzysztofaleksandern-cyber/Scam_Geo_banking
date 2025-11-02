from __future__ import annotations
from typing import Iterable, List
from urllib.parse import quote
from .common_fetch import _get, extract_visible_text, WebItem, rate_limit


# Uses YouTube public RSS (stable, no auth)
# channel_id: UCxxxxxxxxxxxxxxxx
RSS_TMPL = "https://www.youtube.com/feeds/videos.xml?channel_id={cid}"




def fetch_channel_recent(channel_id: str, limit: int = 10) -> List[WebItem]:
url = RSS_TMPL.format(cid=quote(channel_id))
r = _get(url)
# Basic XML scrape without extra deps
# We extract <entry><link href>, <title>
import xml.etree.ElementTree as ET
root = ET.fromstring(r.text)
ns = {"a": "http://www.w3.org/2005/Atom"}
items: List[WebItem] = []
for entry in root.findall("a:entry", ns)[:limit]:
link = entry.find("a:link", ns).attrib.get("href")
title = (entry.findtext("a:title", namespaces=ns) or "").strip()
# Fetch the watch page for textual signals
page = _get(link)
text = extract_visible_text(page.text)
items.append(WebItem("youtube", channel_id, link, title, text, extra={}))
rate_limit(0.6)
return items