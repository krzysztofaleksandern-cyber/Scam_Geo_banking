# tg_admin_infer.py
# Autor: dla projektu Scam_Geo
# Cel: z najnowszego admin_dump_*.json (i opcjonalnie admins_flat.csv) zrobiÄ‡
#      ranking adminÃ³w i zestawienie per kanaÅ‚ + krÃ³tki raport .md

import os, sys, json, csv, glob, datetime
from collections import defaultdict, Counter

OUTDIR = "scam_hunter_out"

def _latest(pattern: str) -> str | None:
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None

def _json_load_any(path: str):
    # Czyta JSON niezaleÅ¼nie od BOM/UTF-8
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("utf-8-sig"))

def _safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def normalize_admin(rec: dict) -> dict:
    """
    Ujednolica rekord admina z rÃ³Å¼nych ÅºrÃ³deÅ‚.
    Oczekiwane potencjalne klucze: id, user_id, name, title, username, is_creator, handle, phone
    """
    aid = rec.get("id") or rec.get("user_id") or rec.get("admin_id")
    uname = rec.get("username") or rec.get("user") or rec.get("handle")
    # nazwa wyÅ›wietlana:
    name = rec.get("name") or rec.get("title") or rec.get("display_name")
    is_creator = bool(rec.get("is_creator")) if "is_creator" in rec else False
    phone = rec.get("phone") if "phone" in rec else None
    return {
        "id": str(aid) if aid is not None else "",
        "username": (uname or "").strip() or "",
        "name": (name or "").strip() or "",
        "is_creator": is_creator,
        "phone": phone or ""
    }

def collect_from_admin_dump(path: str):
    """
    Zwraca:
      - admins_by_channel: dict[channel_handle] -> list[admin_record]
      - all_admins: lista wszystkich rekordÃ³w adminÃ³w (z powtÃ³rzeniami) do rankingu
      - channels_meta: dict[handle] -> {"title": str}
    """
    data = _json_load_any(path)
    admins_by_channel = defaultdict(list)
    channels_meta = {}
    all_admins = []

    if isinstance(data, dict) and "channels" in data:
        iterable = data["channels"]
    elif isinstance(data, list):
        # czÄ™Å›Ä‡ wczeÅ›niejszych dumpÃ³w byÅ‚a listÄ… kanaÅ‚Ã³w
        iterable = data
    else:
        iterable = []

    for ch in iterable:
        handle = ch.get("handle") or ch.get("username") or ""
        title = ch.get("title") or ""
        channels_meta[handle] = {"title": title}
        # "admins" moÅ¼e byÄ‡ brak/None/lista
        admins = ch.get("admins") or []
        for a in admins:
            norm = normalize_admin(a)
            norm["_channel"] = handle
            admins_by_channel[handle].append(norm)
            all_admins.append(norm)

    return admins_by_channel, all_admins, channels_meta

def collect_from_flat_csv(csv_path: str):
    """
    Oczekiwany format (elastyczny): kolumny wÅ›rÃ³d: handle, channel, channel_title, id/user_id/admin_id, username, name/title, is_creator, phone
    Zwraca listÄ™ adminÃ³w (normowanych).
    """
    rows = []
    if not os.path.exists(csv_path):
        return rows

    with open(csv_path, "r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            # zmapuj nazwy
            mapped = {
                "id": r.get("id") or r.get("user_id") or r.get("admin_id"),
                "username": r.get("username"),
                "name": r.get("name") or r.get("title"),
                "is_creator": (r.get("is_creator") in ("1", "True", "true", "YES", "yes")),
                "phone": r.get("phone")
            }
            norm = normalize_admin(mapped)
            norm["_channel"] = r.get("handle") or r.get("channel") or ""
            rows.append(norm)
    return rows

def build_rank(all_admins: list[dict]) -> list[dict]:
    """
    Grupowanie po kluczu toÅ¼samoÅ›ci:
      key = (id if jest) else (username.lower()) else (name.lower())
    """
    buckets = defaultdict(list)

    def identity(a: dict):
        _id = a.get("id", "").strip()
        _un = a.get("username", "").strip().lower()
        _nm = a.get("name", "").strip().lower()
        if _id:
            return ("id", _id)
        if _un:
            return ("username", _un)
        if _nm:
            return ("name", _nm)
        # absolutny fallback â€” unikaj, ale nie gub rekordÃ³w
        return ("raw", json.dumps(a, sort_keys=True, ensure_ascii=False))

    for a in all_admins:
        buckets[identity(a)].append(a)

    ranked = []
    for key, items in buckets.items():
        # agregacja:
        count = len(items)
        is_creator = any(x.get("is_creator") for x in items)
        # bierz najczÄ™Å›ciej wystÄ™pujÄ…cÄ… nazwÄ™/username
        usernames = [x.get("username") for x in items if x.get("username")]
        names = [x.get("name") for x in items if x.get("name")]
        channels = [x.get("_channel") for x in items if x.get("_channel")]

        top_un = Counter(usernames).most_common(1)[0][0] if usernames else ""
        top_nm = Counter(names).most_common(1)[0][0] if names else ""

        ranked.append({
            "identity_key": f"{key[0]}:{key[1]}",
            "username": top_un,
            "name": top_nm,
            "is_creator_any": "1" if is_creator else "0",
            "channels_count": len(set(filter(None, channels))),
            "occurrences": count,
            "channels_sample": ", ".join(sorted(set(filter(None, channels))))[:300]
        })

    # sort: najpierw creatorzy, potem po liczbie wystÄ…pieÅ„, potem po liczbie kanaÅ‚Ã³w
    ranked.sort(key=lambda r: (r["is_creator_any"] != "1", -r["occurrences"], -r["channels_count"], r["identity_key"]))
    return ranked

def write_csv(path: str, rows: list[dict], fieldnames: list[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fieldnames)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in fieldnames})

def write_admins_by_channel(path: str, admins_by_channel: dict, channels_meta: dict):
    # spÅ‚aszczamy adminÃ³w per kanaÅ‚
    rows = []
    for handle, admins in admins_by_channel.items():
        title = _safe_get(channels_meta, handle, "title", default="")
        for a in admins:
            rows.append({
                "channel_handle": handle,
                "channel_title": title,
                "admin_id": a.get("id", ""),
                "admin_username": a.get("username", ""),
                "admin_name": a.get("name", ""),
                "is_creator": "1" if a.get("is_creator") else "0",
                "phone": a.get("phone", "")
            })
    write_csv(
        path,
        rows,
        ["channel_handle", "channel_title", "admin_id", "admin_username", "admin_name", "is_creator", "phone"]
    )

def write_md_summary(path: str, ranked: list[dict], limit: int = 25):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Suspect Admins â€” {now}\n\n")
        f.write("Å¹rÃ³dÅ‚a: `admin_dump_*.json`, `admins_flat.csv` (jeÅ›li obecny)\n\n")
        f.write("| # | Identity | Username | Name | Creator | Occur. | Channels | Sample |\n")
        f.write("|---|----------|----------|------|---------|--------|----------|--------|\n")
        for i, r in enumerate(ranked[:limit], start=1):
            f.write(
                f"| {i} | `{r['identity_key']}` | `{r['username']}` | {r['name']} | "
                f"{'âœ…' if r['is_creator_any']=='1' else ''} | {r['occurrences']} | {r['channels_count']} | "
                f"{r['channels_sample']} |\n"
            )

def main():
    # 1) WejÅ›cie
    inp = None
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        inp = sys.argv[1]
    else:
        inp = _latest(os.path.join(OUTDIR, "admin_dump_*.json"))
    if not inp:
        print("[ERR] Brak pliku admin_dump_*.json w scam_hunter_out/ i nie podano Å›cieÅ¼ki.")
        sys.exit(1)

    print(f"[INFO] Å¹rÃ³dÅ‚o: {inp}")

    # 2) Zbierz adminÃ³w z JSON (per channel + global)
    admins_by_channel, all_admins_json, channels_meta = collect_from_admin_dump(inp)

    # 3) DoÅ‚Ã³Å¼ z admins_flat.csv (jeÅ›li istnieje)
    flat_csv = os.path.join(OUTDIR, "admins_flat.csv")
    all_admins_flat = collect_from_flat_csv(flat_csv)

    # 4) PoÅ‚Ä…cz wszystko do rankingu
    all_admins = list(all_admins_json) + list(all_admins_flat)
    ranked = build_rank(all_admins)

    # 5) Zapisy
    out_rank = os.path.join(OUTDIR, "admins_rank.csv")
    write_csv(
        out_rank,
        ranked,
        ["identity_key", "username", "name", "is_creator_any", "occurrences", "channels_count", "channels_sample"]
    )
    out_by_ch = os.path.join(OUTDIR, "admins_by_channel.csv")
    write_admins_by_channel(out_by_ch, admins_by_channel, channels_meta)

    out_md = os.path.join(OUTDIR, "suspect_admins.md")
    write_md_summary(out_md, ranked, limit=25)

    # 6) Podsumowanie
    print(f"[OK] admins_rank.csv  -> {out_rank}  (rekordÃ³w: {len(ranked)})")
    print(f"[OK] admins_by_channel.csv -> {out_by_ch}")
    print(f"[OK] suspect_admins.md -> {out_md}")

    # krÃ³tki top-5 na stdout
    print("\n[Top 5 â€” szybki podglÄ…d]")
    for i, r in enumerate(ranked[:5], start=1):
        print(f"  {i:>2}. {r['identity_key']} | @{r['username']} | {r['name']} | creator={r['is_creator_any']} | occ={r['occurrences']} | ch={r['channels_count']}")

if __name__ == "__main__":
    main()




