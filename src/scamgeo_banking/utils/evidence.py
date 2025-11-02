import hashlib
import json
import os
import time
import zipfile
from typing import List, Dict, Optional


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(root: str) -> List[str]:
    files: List[str] = []
    for base, _dirs, names in os.walk(root):
        for n in names:
            fp = os.path.join(base, n)
            if os.path.isfile(fp):
                files.append(fp)
    return files


def build_manifest(root: str, extra_meta: Optional[Dict] = None) -> Dict:
    root_abs = os.path.abspath(root)
    files = collect_files(root_abs)
    items = []
    for f in files:
        items.append(
            {
                "path": os.path.relpath(f, root_abs).replace("\\", "/"),
                "sha256": sha256_file(f),
                "bytes": os.path.getsize(f),
            }
        )
    manifest: Dict = {
        "created_utc": int(time.time()),
        "root": root_abs,
        "count_files": len(items),
        "files": items,
    }
    if extra_meta:
        manifest["meta"] = extra_meta
    return manifest


def write_manifest(root: str, manifest: Dict, filename: str = "manifest.json") -> str:
    out = os.path.join(root, filename)
    os.makedirs(root, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return out


def make_zip(root: str, zip_path: str) -> str:
    root_abs = os.path.abspath(root)
    os.makedirs(os.path.dirname(os.path.abspath(zip_path)) or ".", exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for base, _dirs, names in os.walk(root_abs):
            for n in names:
                fp = os.path.join(base, n)
                arc = os.path.relpath(fp, root_abs).replace("\\", "/")
                z.write(fp, arcname=arc)
    return os.path.abspath(zip_path)




