
import os, json, hashlib, zipfile, time
from datetime import datetime, timezone

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def build_evidence_zip(out_dir, zip_path, meta:dict=None):
    """
    Packs all files from out_dir into a ZIP and adds manifest.json with:
      - sha256 of each file
      - created_utc, case_id, tool_version (if provided)
    """
    out_dir = os.path.abspath(out_dir)
    files = []
    for root, _, fs in os.walk(out_dir):
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, out_dir)
            files.append((rel, p))
    files.sort()
    manifest = {
        "created_utc": datetime.now(tz=timezone.utc).isoformat(),
        "case_id": (meta or {}).get("case_id"),
        "tool_version": (meta or {}).get("tool_version"),
        "artifacts": []
    }
    for rel, p in files:
        manifest["artifacts"].append({
            "path": rel,
            "sha256": _sha256(p),
            "size": os.path.getsize(p),
        })
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for rel, p in files:
            z.write(p, arcname=rel)
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
    return zip_path
