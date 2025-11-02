import time, subprocess, sys, os, datetime

PY = sys.executable
LOOP_MIN = 15
while True:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] RUN deep scrape + refresh + whois")
    # 1) głębszy TG scrape
    subprocess.run([PY, "tg_deep_scrape.py"], check=False)
    # 2) odśwież domeny
    subprocess.run([PY, "domains_refresh.py"], check=False)
    # 3) whois/asn
    p = subprocess.run([PY, "whois_asn_geo.py", "scam_hunter_out/domains_to_check.txt"], capture_output=True, text=True)
    if p.stdout:
        with open("scam_hunter_out/whois_snapshot.jsonl","a",encoding="utf-8") as f:
            f.write(p.stdout.strip()+"\n")
    # 4) szybki CSV do przeglądu (domeny + AS)
    try:
        import json,csv
        last = json.loads(p.stdout)
        with open("scam_hunter_out/whois_flat.csv","a",newline='',encoding="utf-8") as cf:
            w = csv.writer(cf)
            for row in last:
                w.writerow([row["domain"], row["ip"], row["ipwhois"]["asn"], row["ipwhois"]["network"]["name"]])
    except Exception as e:
        pass
    # 5) śpij
    time.sleep(LOOP_MIN*60)
