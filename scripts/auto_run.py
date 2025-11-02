# 1) odśwież seeds + scrape + domains
python extract_seeds_v2.py
python tg_deep_scrape.py
python domains_refresh.py

# 2) whois + geo score + raporty
python whois_asn_geo.py scam_hunter_out\domains_to_check.txt | Set-Content scam_hunter_out\whois_last.json -Encoding utf8
python geo_scorer.py
python geo_visual_report.py

# 3) lingwistyka (HTML export lub ostatni deep_report/admin_dump)
python geo_linguistic_probe.py messages.html
