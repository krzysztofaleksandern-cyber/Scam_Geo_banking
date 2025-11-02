#!/usr/bin/env python3
"""
run_all.py
Orkiestracja pipeline OSINT: uruchamia skrypty w ustalonej kolejności,
loguje, tworzy checksums i evidence bundle.
Uruchom: python run_all.py
"""

import subprocess, os, sys, time, json, hashlib, shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(ROOT, "scam_hunter_out")
os.makedirs(OUTDIR, exist_ok=True)

LOGFILE = os.path.join(OUTDIR, f"run_all_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

def log(msg):
    ts = datetime.now().isoformat(sep=' ', timespec='seconds')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_cmd(cmd, cwd=ROOT, timeout=None):
    log(f"RUN: {cmd}")
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        log("EXIT CODE: " + str(p.returncode))
        if p.stdout:
            log("STDOUT: " + p.stdout.strip()[:2000])
        if p.stderr:
            log("STDERR: " + p.stderr.strip()[:2000])
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        log("ERROR: timeout")
        return 124, "", "timeout"

def checksum_file(path):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b = f.read(65536)
            if not b: break
            h.update(b)
    return h.hexdigest()

def safe_copy(src, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(src))
    shutil.copy2(src, dst)
    return dst

def main():
    log("START run_all pipeline")

    # 1) Geo-linguistic probe (you have it but run again for fresh parse)
    if os.path.exists("geo_linguistic_probe.py"):
        run_cmd("python geo_linguistic_probe.py messages.html", timeout=60)

    # 2) Scamhunter full (crawl Telegram public handles + web seeds)
    if os.path.exists("scam_hunter_full.py"):
        run_cmd("python scam_hunter_full.py", timeout=600)

    # 3) Whois/ASN/Geo - gather domains found in scam_hunter_out/report.json
    report_path = os.path.join(OUTDIR, "report.json")
    domains_txt = os.path.join(OUTDIR, "domains_to_check.txt")
    if os.path.exists(report_path):
        try:
            rpt = json.load(open(report_path,"r",encoding="utf-8"))
            urls = rpt.get("found_urls",[]) or []
            # extract domains
            ds = set()
            from urllib.parse import urlparse
            for u in urls:
                try:
                    p = urlparse(u)
                    if p.netloc:
                        ds.add(p.netloc)
                except:
                    pass
            with open(domains_txt,"w",encoding="utf-8") as f:
                for d in sorted(ds):
                    f.write(d+"\n")
            log(f"Saved domains list: {domains_txt} ({len(ds)} entries)")
        except Exception as e:
            log("Could not parse report.json: " + str(e))

    if os.path.exists("whois_asn_geo.py") and os.path.exists(domains_txt):
        # whois_asn_geo.py expects a domains.txt with one domain per line
        run_cmd(f"python whois_asn_geo.py {domains_txt}", timeout=300)

    # 4) OCR on screenshots (if folder exists)
    screenshots_dir = os.path.join(ROOT, "screenshots")
    if os.path.isdir(screenshots_dir) and os.path.exists("ocr_pipeline.py"):
        run_cmd(f"python ocr_pipeline.py \"{screenshots_dir}\"", timeout=300)
    else:
        log("No screenshots folder or ocr_pipeline.py missing; skipping OCR")

    # 5) ping_test for MTProto servers (if file present)
    if os.path.exists("ping_test.py"):
        run_cmd("python ping_test.py", timeout=60)

    # 6) Build evidence bundle (zip + pdf)
    if os.path.exists("evidence_pack.py"):
        run_cmd("python evidence_pack.py", timeout=120)

    # 7) Create checksums for all outputs
    log("Generating checksums for output files")
    checksums = {}
    for root,_,files in os.walk(OUTDIR):
        for fn in files:
            path = os.path.join(root,fn)
            try:
                checksums[os.path.relpath(path, OUTDIR)] = checksum_file(path)
            except Exception as e:
                log("Checksum error for "+path+" : "+str(e))
    cs_path = os.path.join(OUTDIR, "checksums.json")
    with open(cs_path,"w",encoding="utf-8") as f:
        json.dump(checksums, f, indent=2)
    log(f"Checksums saved to {cs_path}")

    log("RUN_ALL finished. Outputs in " + OUTDIR)
    print("\nFINAL SUMMARY: outputs saved in", OUTDIR)
    print("Copy evidence_bundle.zip and evidence_summary.pdf to external drive and send to police/revolut as needed.")

if __name__ == "__main__":
    main()
