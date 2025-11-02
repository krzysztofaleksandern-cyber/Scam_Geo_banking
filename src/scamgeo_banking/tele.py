from __future__ import annotations
import os
from telethon import TelegramClient
from .utils.config import Config

def make_client(cfg: Config):
    creds = cfg.get_telegram_credentials()
    api_id = creds["api_id"]
    api_hash = creds["api_hash"]
    session_name = creds["session_name"] or "scamhunter.session"

    if not api_id or not api_hash:
        raise RuntimeError("Brak TELEGRAM_API_ID/TELEGRAM_API_HASH (ENV) ani wartoÅ›ci w configu.")

    # Uwaga: NIE logujemy nigdy api_hash
    print(f"[TELEGRAM] session={session_name}, api_id={api_id}")

    client = TelegramClient(session_name, api_id, api_hash)
    return client




