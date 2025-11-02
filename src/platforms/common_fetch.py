from __future__ import annotations
import re, time
from typing import Iterable, Dict, Any
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup


DEFAULT_UA = (
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
"(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass
class WebItem:
platform: str
source: str # URL or handle
url: str # canonical post/video url
title: str | None
text: str | None
extra: Dict[str, Any]




def _get(url: str, timeout: int = 15) -> requests.Response:
r = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=timeout)
r.raise_for_status()
return r




def extract_visible_text(html: str) -> str:
soup = BeautifulSoup(html, "html.parser")
for tag in soup(["script", "style", "noscript"]):
tag.decompose()
txt = soup.get_text(" ", strip=True)
return re.sub(r"\s+", " ", txt)




def rate_limit(s: float = 0.8):
time.sleep(s)