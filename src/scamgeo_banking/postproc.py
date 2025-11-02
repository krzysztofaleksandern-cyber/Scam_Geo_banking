from __future__ import annotations
from pathlib import Path
from datetime import datetime
import csv, json, hashlib, zipfile, re

def score_and_export_iocs(out_dir: Path, cfg: dict) -> list[dict]:
    out_dir = Path(out_dir)
    ioc_csv = out_dir / "iocs.csv"; iocs = []
    if ioc_csv.exists():
        with ioc_csv.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                url = row.get("url") or row.get("ioc") or ""
                score = int(row.get("score", "60") or 60)
                iocs.append({"type":"url", "value":url, "score":score})
    else:
        iocs = [
            {"type":"url","value":"https://erste-bonus-secure.com/login","score":85},
            {"type":"url","value":"https://raiffe1sen-secure.net","score":70},
        ]
        with ioc_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["type","url","score"])
            w.writeheader()
            for i in iocs: w.writerow({"type":i["type"], "url":i["value"], "score":i["score"]})
    (out_dir / "iocs.txt").write_text("\n".join(i["value"] for i in iocs), encoding="utf-8")
    return iocs

def enrich_whois_and_reputation(out_dir: Path, iocs: list[dict], cfg: dict):
    out_dir = Path(out_dir)
    whois_csv = out_dir / "whois_enriched.csv"; rep_csv = out_dir / "url_reputation.csv"
    with whois_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["domain","created","registrar","status"])
        w.writeheader()
        for i in iocs:
            domain = extract_domain(i["value"])
            w.writerow({"domain": domain, "created": "2023-01-01", "registrar": "Demo Registrar", "status": "clientTransferProhibited"})
    with rep_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["url","engine","score","detail"])
        w.writeheader()
        for i in iocs:
            w.writerow({"url":i["value"], "engine":"VT",  "score": 1, "detail":"demo-positive"})
            w.writerow({"url":i["value"], "engine":"OTX", "score": 1, "detail":"demo-pulse"})

def extract_domain(url: str) -> str:
    m = re.search(r'https?://([^/]+)', url or "")
    return m.group(1).lower() if m else "n/a"

def enrich_asn(out_dir: Path, iocs: list[dict]):
    out_dir = Path(out_dir)
    asn_csv = out_dir / "asn_enriched.csv"
    with asn_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["domain","asn","org"])
        w.writeheader()
        for i in iocs:
            domain = extract_domain(i["value"])
            w.writerow({"domain":domain, "asn":"AS65535", "org":"DemoNet Ltd."})

def export_stix(out_dir: Path, iocs: list[dict]):
    out_dir = Path(out_dir); stix_path = out_dir / "stix_bundle.json"
    objs = []; now = datetime.utcnow().isoformat()+"Z"
    for idx, i in enumerate(iocs, start=1):
        if i["type"] == "url":
            objs.append({
                "type":"indicator","spec_version":"2.1","id":f"indicator--demo-{idx:04d}",
                "created":now,"modified":now,"pattern_type":"stix",
                "pattern": f"[url:value = '{i['value']}']","valid_from": now,
                "labels": ["fraud","banking-abuse"],"confidence": min(100, int(i["score"]))
            })
    stix = {"type":"bundle","id":"bundle--demo","objects":objs}
    stix_path.write_text(json.dumps(stix, indent=2), encoding="utf-8")

def export_misp(out_dir: Path, iocs: list[dict], cfg: dict):
    out_dir = Path(out_dir); misp = {"Event":{"info":"Scam_Geo export (demo)","Attribute":[]}}
    for i in iocs:
        if i["type"] == "url":
            misp["Event"]["Attribute"].append({"type":"url","value":i["value"],"comment":"banking-abuse","to_ids":True})
    (out_dir/"misp_export.json").write_text(json.dumps(misp, indent=2), encoding="utf-8")

def generate_pdf_report(out_dir: Path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        return
    out_dir = Path(out_dir); pdf = out_dir / "report.pdf"
    c = canvas.Canvas(str(pdf), pagesize=A4); w, h = A4
    c.setFont("Helvetica-Bold", 16); c.drawString(40, h-60, "Scam_Geo — Banking Abuse Report (demo)")
    c.setFont("Helvetica", 10); c.drawString(40, h-80, f"Generated: {datetime.utcnow().isoformat()}Z")
    c.drawString(40, h-100, "Artifacts: iocs.csv, whois_enriched.csv, url_reputation.csv, stix_bundle.json")
    c.showPage(); c.save()

def build_manifest_and_zip(out_dir: Path, zip_path: str):
    out_dir = Path(out_dir); zip_file = Path(zip_path)
    def _sha256(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for ch in iter(lambda: f.read(1<<20), b""): h.update(ch)
        return h.hexdigest()
    files = []
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as z:
        for fp in out_dir.rglob("*"):
            if fp.is_file():
                z.write(fp, fp.relative_to(out_dir))
                files.append({"path": str(fp.relative_to(out_dir)), "sha256": _sha256(fp)})
    manifest = {"created_at": datetime.utcnow().isoformat()+"Z","zip_path": str(zip_file), "zip_sha256": _sha256(zip_file), "artifacts": files}
    (out_dir/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

def append_audit(out_dir: Path, message: str):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.utcnow().isoformat()}Z {message}\n"
    with (out_dir/"audit.log").open("a", encoding="utf-8") as f: f.write(line)




