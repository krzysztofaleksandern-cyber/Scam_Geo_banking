from __future__ import annotations
from typing import List
from urllib.parse import quote
from .common_fetch import _get, extract_visible_text, WebItem, rate_limit


# Public page feed via mbasic (lighter HTML). No login.
PAGE_TMPL = "https://mbasic.facebook.com/{page}"




def fetch_page_recent(page_id_or_name: str, limit: int = 10) -> List[WebItem]:
url = PAGE_TMPL.format(page=quote(page_id_or_name))
page = _get(url)
text = extract_visible_text(page.text)
return [WebItem("facebook", page_id_or_name, url, title=f"Facebook {page_id_or_name}", text=text, extra={"limit": limit})]