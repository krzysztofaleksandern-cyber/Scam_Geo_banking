#!/usr/bin/env python3
# run_all.py – pełny pipeline do tropienia scamera
# © 2025
import os
import subprocess
import datetime
from pathlib import Path

OUTDIR = "scam_hunter_out"
Path(OUTDIR).mkdir(exist_ok=True)

def log(msg):
    ts = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{ts} {msg}")

def run_cmd(cmd, timeout=120):
    log(f"RUN: {cmd}")
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        print(res.stdout)
        if res.stderr:
            print(res.stderr)
        log(f"EXIT CODE: {res.returncode}")
        if res.returncode != 0:
            log(f"STDERR: {res.stderr.strip()}")
        else:
            log(f"STDOUT: {res.stdout.strip()[:400]}")
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: {cmd}")
    except KeyboardInterrupt:
        log("User aborted.")
    return res.returncode if 'res' in locals() else -1


def main():
    log("START run_all pipeline")

    # 0️⃣ Ekstrakcja seedów (z messages.html, channels.csv, manual_seeds.txt)
    if os.path.exists("extract_seeds_v2.py"):
        run_cmd("python extract_seeds_v2.py", timeout=90)

    # 1️⃣ Analiza językowa czatu
    if os.path.exists("messages.html"):
        run_cmd("python geo_linguistic_probe.py messages.html", timeout=90)
    else:
        log("messages.html not found, skipping linguistic probe.")

    # 2️⃣ Główna analiza kanałów i powiązań scamera
    if os.path.exists("scam_hunter_full.py"):
        run_cmd("python scam_hunter_full.py", timeout=240)
    else:
        log("scam_hunter_full.py not found, skipping.")

    # 3️⃣ Uzupełnienie pustych domen z HTML (fallback)
    domains_txt = os.path.join(OUTDIR, "domains_to_check.txt")
    html_urls = os.path.join(OUTDIR, "html_urls.txt")
    if os.path.exists(domains_txt) and os.path.getsize(domains_txt) == 0 and os.path.exists(html_urls):
        from urllib.parse import urlparse
        ds = set()
        for line in open(html_urls, "r", encoding="utf-8"):
            line = line.strip()
            if not line: 
                continue
            try:
                p = urlparse(line)
                if p.netloc:
                    ds.add(p.netloc)
            except:
                pass
        with open(domains_txt, "w", encoding="utf-8") as f:
            for d in sorted(ds):
                f.write(d + "\n")
        log(f"Filled domains_from_html: {domains_txt} ({len(ds)} entries)")

    # 4️⃣ WHOIS / ASN / GEO IP
    if os.path.exists(domains_txt):
        run_cmd(f"python whois_asn_geo.py {domains_txt}", timeout=120)
    else:
        log("No domain list, skipping WHOIS.")

    # 5️⃣ OCR (jeśli folder screenshots istnieje)
    if os.path.exists("ocr_pipeline.py") and os.path.isdir("screenshots"):
        run_cmd("python ocr_pipeline.py", timeout=180)
    else:
        log("No screenshots folder or ocr_pipeline.py missing; skipping OCR")

    # 6️⃣ Test połączenia z serwerami MTProto (ping)
    if os.path.exists("ping_test.py"):
        run_cmd("python ping_test.py", timeout=30)
    else:
        log("ping_test.py missing; skipping network test.")

    log("=== KONIEC PIPELINE ===")

if __name__ == "__main__":
    main()
