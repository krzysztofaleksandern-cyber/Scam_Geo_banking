from __future__ import annotations
from typing import List
from urllib.parse import quote
from .common_fetch import _get, extract_visible_text, WebItem, rate_limit


# Public profile page scrape (no login). TikTok changes often; we only need visible text for IOC/keywords.
# handle: without @, e.g., "binance_invest_2024"


PROFILE_TMPL = "https://www.tiktok.com/@{handle}"




def fetch_profile_recent(handle: str, limit: int = 10) -> List[WebItem]:
url = PROFILE_TMPL.format(handle=quote(handle))
page = _get(url)
text = extract_visible_text(page.text)
# We don't reliably parse individual post URLs here (heavy JS). We still feed text into IOC + keyword scorer.
# To keep schema, we return a single WebItem for the profile "recent" text block.
return [WebItem("tiktok", handle, url, title=f"TikTok @{handle}", text=text, extra={"limit": limit})]