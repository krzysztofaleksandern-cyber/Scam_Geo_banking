import argparse, json, hashlib, os, pathlib, time, zipfile

def sha256(p): 
    h=hashlib.sha256(); 
    with open(p,'rb') as f: 
        for chunk in iter(lambda:f.read(1<<20), b''): h.update(chunk)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser(prog='scamgeo_banking evidence', description='Manifest + evidence.zip')
    p.add_argument('-d','--dir', required=True, help='katalog z artefaktami')
    p.add_argument('--zip', required=True, help='ścieżka docelowa evidence.zip')
    args = p.parse_args()
    outzip = pathlib.Path(args.zip)
    base = pathlib.Path(args.dir)
    with zipfile.ZipFile(outzip,'w',zipfile.ZIP_DEFLATED) as z:
        files=[]
        for fp in base.rglob('*'):
            if fp.is_file():
                z.write(fp, fp.relative_to(base))
                files.append({"path": str(fp.relative_to(base)), "sha256": sha256(fp)})
    manifest = {
        "created_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "zip_path": str(outzip), "zip_sha256": sha256(outzip),
        "artifacts": files
    }
    mpath = base / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f"[EVIDENCE] OK → {outzip} | manifest: {mpath}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())




