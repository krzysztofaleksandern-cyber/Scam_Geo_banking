from dataclasses import dataclass
from typing import Optional, List
import os

def _split_list(v: Optional[str]) -> List[str]:
    if not v: return []
    return [x.strip() for x in v.split(",") if x.strip()]

@dataclass(frozen=True)
class AppConfig:
    env: str; debug: bool
    telegram_api_id: Optional[str]; telegram_api_hash: Optional[str]
    virustotal_api_key: Optional[str]; whois_api_key: Optional[str]
    proxy_list: list[str]; request_timeout_s: int; max_retries: int; backoff_base_s: float
    @property
    def demo_mode(self) -> bool: return not (self.telegram_api_id and self.telegram_api_hash)

def load_config() -> "AppConfig":
    env=os.getenv("APP_ENV","dev"); debug=os.getenv("APP_DEBUG","1")=="1"
    return AppConfig(env, debug,
        os.getenv("TELEGRAM_API_ID"), os.getenv("TELEGRAM_API_HASH"),
        os.getenv("VIRUSTOTAL_API_KEY"), os.getenv("WHOIS_API_KEY"),
        _split_list(os.getenv("PROXY_LIST")), int(os.getenv("REQUEST_TIMEOUT_S","20")),
        int(os.getenv("MAX_RETRIES","3")), float(os.getenv("BACKOFF_BASE_S","0.6")))




