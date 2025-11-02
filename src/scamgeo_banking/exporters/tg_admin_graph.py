# tg_admin_graph.py
# Autor: dla projektu Scam_Geo
# Cel: ZbudowaÄ‡ graf poÅ‚Ä…czeÅ„ kanaÅ‚Ã³w â†” adminÃ³w i wygenerowaÄ‡ .csv, .gv oraz .png

import os, sys, json, csv, glob, datetime
from collections import defaultdict
import graphviz

OUTDIR = "scam_hunter_out"

def _latest(pattern: str):
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None

def _json_load_any(path: str):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("utf-8-sig"))

def normalize_admin(rec: dict):
    return {
        "id": str(rec.get("id") or rec.get("user_id") or rec.get("admin_id") or ""),
        "username": (rec.get("username") or rec.get("user") or "").strip(),
        "name": (rec.get("name") or rec.get("title") or "").strip(),
        "is_creator": bool(rec.get("is_creator")) if "is_creator" in rec else False
    }

def collect_admin_links(path: str):
    data = _json_load_any(path)
    links = []  # (channel, admin_username)
    if isinstance(data, dict) and "channels" in data:
        iterable = data["channels"]
    elif isinstance(data, list):
        iterable = data
    else:
        iterable = []

    for ch in iterable:
        handle = ch.get("handle") or ch.get("username") or ""
        title = ch.get("title") or handle
        admins = ch.get("admins") or []
        for a in admins:
            adm = normalize_admin(a)
            uname = adm["username"] or adm["name"] or adm["id"]
            if uname:
                links.append({
                    "channel": handle,
                    "channel_title": title,
                    "admin": uname,
                    "admin_name": adm["name"],
                    "is_creator": "1" if adm["is_creator"] else "0"
                })
    return links

def write_csv(path: str, rows: list[dict], fields: list[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in fields})

def build_graph(links: list[dict], out_gv: str, out_png: str):
    dot = graphviz.Graph("AdminGraph", format="png", engine="sfdp")  # sfdp = Å‚adna sieÄ‡
    dot.attr("graph", rankdir="LR", overlap="false", splines="true", bgcolor="#1E1E1E")
    dot.attr("node", shape="ellipse", style="filled", fontname="Arial", fontsize="10", color="white", fillcolor="#444444", fontcolor="white")

    channels = set(l["channel"] for l in links if l["channel"])
    admins = set(l["admin"] for l in links if l["admin"])

    # Dodaj kanaÅ‚y (na niebiesko)
    for ch in sorted(channels):
        dot.node(f"ch_{ch}", label=ch, fillcolor="#004C99", shape="box")

    # Dodaj adminÃ³w (na pomaraÅ„czowo)
    for adm in sorted(admins):
        dot.node(f"adm_{adm}", label=adm, fillcolor="#CC6600")

    # KrawÄ™dzie kanaÅ‚ â†” admin
    for l in links:
        ch_node = f"ch_{l['channel']}"
        adm_node = f"adm_{l['admin']}"
        color = "#66FF66" if l.get("is_creator") == "1" else "#CCCCCC"
        dot.edge(ch_node, adm_node, color=color)

    os.makedirs(os.path.dirname(out_gv), exist_ok=True)
    dot.save(out_gv)
    dot.render(filename=out_gv, format="png", cleanup=True)
    os.replace(out_gv + ".png", out_png)
    print(f"[OK] Wygenerowano graf: {out_png}")

def main():
    inp = None
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        inp = sys.argv[1]
    else:
        inp = _latest(os.path.join(OUTDIR, "admin_dump_*.json"))
    if not inp:
        print("[ERR] Nie znaleziono admin_dump_*.json")
        sys.exit(1)

    print(f"[INFO] Å¹rÃ³dÅ‚o danych: {inp}")
    links = collect_admin_links(inp)
    print(f"[INFO] PowiÄ…zaÅ„ adminâ€“kanaÅ‚: {len(links)}")

    out_csv = os.path.join(OUTDIR, "admin_graph.csv")
    write_csv(out_csv, links, ["channel", "channel_title", "admin", "admin_name", "is_creator"])
    print(f"[OK] Zapisano CSV: {out_csv}")

    out_gv = os.path.join(OUTDIR, "admin_graph.gv")
    out_png = os.path.join(OUTDIR, "admin_graph.png")
    build_graph(links, out_gv, out_png)

if __name__ == "__main__":
    main()




