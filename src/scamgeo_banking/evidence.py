import hashlib, json, os, socket, time
from zipfile import ZipFile, ZIP_DEFLATED
from .version import __version__

def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def build_manifest(root_dir: str) -> dict:
    files = []
    for base, _, names in os.walk(root_dir):
        for name in names:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root_dir).replace("\\", "/")
            st = os.stat(full)
            files.append({"path": rel, "size": st.st_size, "sha256": _sha256(full)})
    return {
        "tool": "Scam_Geo",
        "version": __version__,
        "hostname": socket.gethostname(),
        "generated_utc": int(time.time()),
        "root": os.path.abspath(root_dir),
        "files": files,
    }

def make_zip(root_dir: str, out_zip: str):
    manifest = json.dumps(build_manifest(root_dir), ensure_ascii=False, indent=2).encode("utf-8")
    tmp_manifest = os.path.join(root_dir, "_manifest.json")
    os.makedirs(os.path.dirname(out_zip) or ".", exist_ok=True)
    with open(tmp_manifest, "wb") as f:
        f.write(manifest)
    try:
        with ZipFile(out_zip, "w", ZIP_DEFLATED) as z:
            for base, _, names in os.walk(root_dir):
                for name in names:
                    full = os.path.join(base, name)
                    rel = os.path.relpath(full, root_dir).replace("\\", "/")
                    z.write(full, arcname=rel)
    finally:
        if os.path.exists(tmp_manifest):
            os.remove(tmp_manifest)




