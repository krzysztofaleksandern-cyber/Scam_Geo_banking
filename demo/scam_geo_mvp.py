# scam_geo_mvp.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import socket, re, requests, whois, tldextract
import phonenumbers
from langdetect import detect, LangDetectException

app = FastAPI(title="Scammer Country Inference - MVP")

IP_API_URL = "http://ip-api.com/json/{}"  # free, rate-limited

class ScanRequest(BaseModel):
    type: str  # domain|email|phone|ip|username|wallet
    value: str

def geolocate_ip(ip: str):
    try:
        r = requests.get(IP_API_URL.format(ip), timeout=6)
        j = r.json()
        if j.get("status") == "success":
            return {"ip": ip, "country": j.get("country"), "countryCode": j.get("countryCode"),
                    "region": j.get("regionName"), "city": j.get("city"), "isp": j.get("isp")}
    except Exception:
        return None
    return None

def extract_ips_from_email_headers(raw_headers: str):
    # Look for IPs in Received: lines
    ips = re.findall(r'\[?([0-9]{1,3}(?:\.[0-9]{1,3}){3})\]?', raw_headers)
    # filter valid
    def valid_octets(ip):
        parts = ip.split(".")
        return all(0 <= int(p) <= 255 for p in parts)
    ips = [ip for ip in ips if valid_octets(ip)]
    return list(dict.fromkeys(ips))  # uniq

def resolve_domain_ips(domain: str):
    try:
        # strip possible path
        domain = domain.split("//")[-1].split("/")[0]
        # use socket to get addresses
        ips = []
        try:
            _, _, addrs = socket.gethostbyname_ex(domain)
            ips.extend(addrs)
        except Exception:
            pass
        return list(dict.fromkeys(ips))
    except Exception:
        return []

def parse_phone_country(phone: str):
    try:
        p = phonenumbers.parse(phone, None)
        region = phonenumbers.region_code_for_number(p)
        return region
    except Exception:
        return None

def whois_country(domain: str):
    try:
        w = whois.whois(domain)
        # try common fields
        for f in ("country","registrant_country","registrant_countrycode"):
            if hasattr(w, f) and getattr(w,f):
                return str(getattr(w,f))
        # sometimes it's in address
        for k in ("registrar","org","name"):
            if hasattr(w,k) and getattr(w,k):
                pass
    except Exception:
        return None
    return None

def language_of_text(text: str):
    try:
        return detect(text)
    except LangDetectException:
        return None

@app.post("/infer")
def infer(req: ScanRequest):
    t = req.type.lower()
    v = req.value.strip()
    evidence = []
    scores = {}  # country => points

    # Helper to add points
    def add_points(country, pts, reason):
        if not country:
            return
        country = country.strip()
        scores[country] = scores.get(country, 0) + pts
        evidence.append({"country": country, "points": pts, "reason": reason})

    # 1) IP paths
    if t == "email":
        ips = extract_ips_from_email_headers(v)
        # take first public IP (skip private 10/192/172 ranges)
        for ip in ips:
            if ip.startswith(("10.","192.168.","172.")):
                continue
            geo = geolocate_ip(ip)
            if geo:
                add_points(geo["country"], 40, f"IP from Received: {ip} (isp={geo.get('isp')})")
                break
    elif t == "domain":
        ips = resolve_domain_ips(v)
        for ip in ips:
            geo = geolocate_ip(ip)
            if geo:
                add_points(geo["country"], 40, f"Domain resolved IP: {ip} (isp={geo.get('isp')})")
        # WHOIS
        try:
            wd = whois_country(v)
            if wd:
                add_points(wd, 15, "WHOIS country")
        except Exception:
            pass
    elif t == "ip":
        geo = geolocate_ip(v)
        if geo:
            add_points(geo["country"], 60, f"Direct IP geo: {v}")
    elif t == "phone":
        region = parse_phone_country(v)
        if region:
            add_points(region, 50, f"Phone prefix region: {region}")
    elif t in ("username","wallet"):
        # minimal: try to detect language in username (if contains words) or skip
        lang = language_of_text(v)
        if lang:
            # map lang code to likely country (weak)
            add_points(lang.upper(), 5, "Detected language from username")
    # 2) try detect language if input contains prose (if domain not provided)
    if t in ("email","username","domain"):
        # attempt to detect language of the value (only if looks like sentence)
        if len(v) > 30 and "http" not in v:
            lang = language_of_text(v)
            if lang:
                add_points(lang.upper(), 8, f"Language detection: {lang}")

    # Aggregate best country
    if not scores:
        return {"country": None, "confidence": "low", "score_map": {}, "evidence": evidence}
    # normalize
    best_country, best_score = max(scores.items(), key=lambda x: x[1])
    total_possible = 100  # informal
    normalized = int(min(100, (best_score / total_possible) * 100))
    if normalized >= 70:
        conf = "high"
    elif normalized >= 35:
        conf = "medium"
    else:
        conf = "low"
    return {
        "country": best_country,
        "score": normalized,
        "confidence": conf,
        "score_map": scores,
        "evidence": evidence
    }
