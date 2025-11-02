# tg_admin_dump.py (v3) â€” zbiera teÅ¼ suspected_admins z BIO, pinned i treÅ›ci
import asyncio, json, os, re, datetime
from typing import List, Dict, Any, Tuple

from telethon import TelegramClient, errors
from telethon.tl.types import (
    Channel, Chat, User,
    ChannelParticipantsAdmins, ChannelParticipantCreator,
    MessageEntityMention, MessageEntityMentionName, MessageEntityTextUrl, MessageEntityUrl
)
from telethon.tl.functions.channels import (
    JoinChannelRequest, LeaveChannelRequest, GetFullChannelRequest
)
from telethon.tl.functions.messages import GetMessagesRequest

CONFIG = "config.json"
OUTDIR = "scam_hunter_out"
STAY_JOINED = True   # zostaw doÅ‚Ä…czone kanaÅ‚y â€” czasem po chwili widaÄ‡ wiÄ™cej meta

MENTION_RE = re.compile(r'@([A-Za-z0-9_]{5,})')

def load_config():
    cfg = json.load(open(CONFIG, "r", encoding="utf-8"))
    if "telegram" in cfg:
        t = cfg["telegram"]
        api_id = t["api_id"]; api_hash = t["api_hash"]; session_name = t.get("session_name","session")
    else:
        api_id = cfg["api_id"]; api_hash = cfg["api_hash"]; session_name = cfg.get("session_name","session")
    seeds = cfg.get("seeds", [])
    return api_id, api_hash, session_name, seeds

def add_suspect(bucket: List[Dict[str, Any]], username: str, reason: str, extra: Dict[str, Any] = None):
    if not username: return
    username = username.lstrip('@')
    for s in bucket:
        if s.get("username") == username and s.get("reason") == reason:
            return
    item = {"username": username, "reason": reason}
    if extra: item.update(extra)
    bucket.append(item)

async def collect_admins(client: TelegramClient, entity, dst_info: Dict[str, Any], where: str):
    admins = []
    try:
        async for p in client.iter_participants(entity, filter=ChannelParticipantsAdmins, aggressive=True):
            role = "creator" if getattr(p, "participant", None).__class__.__name__ == "ChannelParticipantCreator" else "admin"
            admins.append({
                "id": getattr(p, "id", None),
                "username": getattr(p, "username", None),
                "first_name": getattr(p, "first_name", None),
                "last_name": getattr(p, "last_name", None),
                "role": role,
                "source": where
            })
    except errors.ChatAdminRequiredError as e:
        dst_info["errors"].append(f"{where}: no rights to list admins ({e.__class__.__name__})")
    except Exception as e:
        dst_info["errors"].append(f"{where}: iter_participants failed: {e}")
    dst_info["admins"].extend(admins)

async def get_full_and_maybe_join(client: TelegramClient, entity) -> Tuple[Any, bool]:
    joined_now = False
    try:
        full = await client(GetFullChannelRequest(entity))
        return full, joined_now
    except Exception:
        pass
    # sprÃ³buj doÅ‚Ä…czyÄ‡ (publiczne)
    try:
        await client(JoinChannelRequest(entity))
        joined_now = True
        full = await client(GetFullChannelRequest(entity))
        return full, joined_now
    except Exception:
        return None, joined_now

async def harvest_mentions_from_text(text: str, bucket: List[Dict[str, Any]], reason: str):
    if not text: return
    for m in MENTION_RE.findall(text):
        add_suspect(bucket, m, reason)

def harvest_mentions_from_entities(msg, bucket: List[Dict[str, Any]]):
    if not getattr(msg, "entities", None): return
    for ent in msg.entities:
        if isinstance(ent, MessageEntityMention):
            # literal "@user" fragment
            if msg.message:
                frag = msg.message[ent.offset:ent.offset+ent.length]
                add_suspect(bucket, frag, "entity_mention")
        elif isinstance(ent, MessageEntityMentionName):
            # â€žwspomnienie po IDâ€ â€” nie ma @, ale mamy user_id
            add_suspect(bucket, None, "entity_mention_name", {"user_id": ent.user_id})
        elif isinstance(ent, (MessageEntityTextUrl, MessageEntityUrl)):
            # URL â€” sprÃ³buj wyÅ‚uskaÄ‡ @ z linku
            if getattr(ent, "url", None):
                m = MENTION_RE.search(ent.url)
                if m: add_suspect(bucket, m.group(1), "entity_url")
            elif msg.message:
                frag = msg.message[ent.offset:ent.offset+ent.length]
                m = MENTION_RE.search(frag)
                if m: add_suspect(bucket, m.group(1), "entity_url")

async def fetch_for_handle(client: TelegramClient, handle: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "handle": handle, "title": None, "type": None,
        "admins": [], "suspected_admins": [], "errors": [], "meta": {}
    }
    try:
        entity = await client.get_entity(handle)
    except Exception as e:
        info["errors"].append(f"get_entity failed: {e}")
        return info

    info["title"] = getattr(entity, "title", None) or getattr(entity, "first_name", None)
    if isinstance(entity, User):
        info["type"] = "user"
        info["errors"].append("entity is a User; skipping admin list")
        # ale zbierz trochÄ™ meta
        info["meta"]["user_id"] = entity.id
        info["meta"]["username"] = entity.username
        return info

    info["type"] = "channel" if isinstance(entity, Channel) else "chat"

    full, joined_now = await get_full_and_maybe_join(client, entity)
    # meta-flagi
    info["meta"]["megagroup"] = bool(getattr(entity, "megagroup", False))
    info["meta"]["broadcast"] = bool(getattr(entity, "broadcast", False))
    info["meta"]["gigagroup"] = bool(getattr(entity, "gigagroup", False))
    info["meta"]["scam"] = bool(getattr(entity, "scam", False))
    info["meta"]["fake"] = bool(getattr(entity, "fake", False))
    info["meta"]["verified"] = bool(getattr(entity, "verified", False))

    # 1) Prawdziwi admini â€” jeÅ›li mamy uprawnienia
    await collect_admins(client, entity, info, "channel")

    # 2) BIO/About â€” czÄ™sto majÄ… â€žKontakt admin: @Xâ€
    about_text = None
    try:
        if full and getattr(full, "full_chat", None):
            about_text = getattr(full.full_chat, "about", None)
            if about_text:
                await harvest_mentions_from_text(about_text, info["suspected_admins"], "about_mention")
    except Exception as e:
        info["errors"].append(f"about parse failed: {e}")

    # 3) pinned message
    try:
        if full and getattr(full.full_chat, "pinned_msg_id", None):
            mid = full.full_chat.pinned_msg_id
            msgs = await client(GetMessagesRequest(id=[mid]))
            if msgs and getattr(msgs, "messages", None):
                msg = msgs.messages[0]
                await harvest_mentions_from_text(getattr(msg, "message", None), info["suspected_admins"], "pinned_mention")
                harvest_mentions_from_entities(msg, info["suspected_admins"])
    except Exception as e:
        info["errors"].append(f"pinned parse failed: {e}")

    # 4) kilka ostatnich wiadomoÅ›ci â€” szukaj @wzmianki
    try:
        async for msg in client.iter_messages(entity, limit=60):
            if not msg: break
            await harvest_mentions_from_text(getattr(msg, "message", None), info["suspected_admins"], "text_mention")
            harvest_mentions_from_entities(msg, info["suspected_admins"])
    except Exception as e:
        info["errors"].append(f"scan_last_msgs failed: {e}")

    # 5) podpiÄ™ta grupa dyskusyjna â€” tam czÄ™sto admini sÄ… jawni
    if full and getattr(full.full_chat, "linked_chat_id", None):
        try:
            linked_id = full.full_chat.linked_chat_id
            linked = await client.get_entity(linked_id)
            await collect_admins(client, linked, info, "linked_discussion")
        except Exception as e:
            info["errors"].append(f"linked discussion failed: {e}")

    # sprzÄ…tanie: opcjonalne wyjÅ›cie
    if joined_now and not STAY_JOINED:
        try: await client(LeaveChannelRequest(entity))
        except Exception: pass

    return info

async def main():
    api_id, api_hash, session_name, seeds = load_config()
    os.makedirs(OUTDIR, exist_ok=True)
    async with TelegramClient(session_name, api_id, api_hash) as client:
        me = await client.get_me()
        print(f"Signed in as: {me!r}")
        out: List[Dict[str, Any]] = []
        for h in seeds:
            print(f"[ADMIN DUMP] {h}")
            out.append(await fetch_for_handle(client, h))
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        path = os.path.join(OUTDIR, f"admin_dump_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"[OK] Saved -> {path}")

if __name__ == "__main__":
    asyncio.run(main())




