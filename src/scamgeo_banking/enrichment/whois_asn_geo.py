import sys, json, socket
from pathlib import Path

# miÄ™kkie importy
try:
    import whois as pywhois
except Exception:
    pywhois = None

try:
    from ipwhois import IPWhois
except Exception:
    IPWhois = None

def resolve_ip(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception:
        return None

def do_whois_domain(domain):
    if not pywhois:
        return {"error":"python-whois not installed"}
    try:
        w = pywhois.whois(domain)
        return {
            "registrar": getattr(w, "registrar", None),
            "creation_date": str(getattr(w, "creation_date", None)),
            "country": getattr(w, "country", None)
        }
    except Exception as e:
        return {"error": repr(e)}

def do_ipwhois(ip):
    if not IPWhois:
        return {"error":"ipwhois not installed"}
    try:
        obj = IPWhois(ip)
        data = obj.lookup_rdap(depth=1)
        net = data.get("network", {}) or {}
        return {
            "asn": data.get("asn"),
            "asn_country_code": data.get("asn_country_code"),
            "network": {
                "handle": net.get("handle"),
                "name": net.get("name"),
                "country": net.get("country"),
                "cidr": net.get("cidr"),
                "type": net.get("type"),
                "status": net.get("status"),
                "remarks": net.get("remarks"),
                "notices": net.get("notices"),
                "links": net.get("links"),
                "events": net.get("events"),
                "start_address": net.get("start_address"),
                "end_address": net.get("end_address"),
            }
        }
    except Exception as e:
        return {"error": repr(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: python whois_asn_geo.py domains.txt")
        sys.exit(1)
    infile = Path(sys.argv[1])
    domains = []
    for line in infile.read_text(encoding="utf-8").splitlines():
        d = line.strip().lower()
        if d and not d.startswith("#"):
            domains.append(d)
    out = []
    for d in sorted(set(domains)):
        ip = resolve_ip(d)
        out.append({
            "domain": d,
            "ip": ip,
            "whois": do_whois_domain(d),
            "ipwhois": do_ipwhois(ip) if ip else {"error": "no ip"}
        })
    print(json.dumps(out, indent=2))
if __name__ == "__main__":
    main()




