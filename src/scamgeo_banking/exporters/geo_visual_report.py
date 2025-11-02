# -*- coding: utf-8 -*-
import json, os, re, csv
from datetime import datetime, timezone
from collections import Counter, defaultdict

# Wykres
import matplotlib.pyplot as plt

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle

OUTDIR = os.path.join("scam_hunter_out")
WHOIS_JSON = os.path.join(OUTDIR, "whois_last.json")  # wymagane
BAR_PNG = os.path.join(OUTDIR, "geo_bar_chart.png")
PDF_PATH = os.path.join(OUTDIR, "geo_visual_report.pdf")
CSV_RISK = os.path.join(OUTDIR, "geo_risk.csv")

SAFE_DOMAINS = {
    "t.me", "youtube.com", "www.youtube.com", "vt.tiktok.com",
    "www.tiktok.com", "api-shein.shein.com", "www.zen.com"
}

SUSPICIOUS_TLDS = {"net", "top", "xyz", "online", "shop", "live", "link"}
SUSPICIOUS_KEYWORDS = {"bitcoin", "crypto", "usdt", "earn", "bonus", "vip", "profit"}
SUSPICIOUS_REGISTRARS = {
    "Gname.com Pte. Ltd.", "NameSilo, LLC", "PDR Ltd.", "Hostinger", "Namecheap, Inc.",
    # Uwaga: Alibaba Cloud bywa legit (SHEIN), wiÄ™c niÅ¼sza waga jeÅ›li brand nieznany
    "Alibaba Cloud Computing (Beijing) Co., Ltd."
}

def read_json_any_bom(path):
    # bezboleÅ›nie Å‚aduje nawet z BOM-em
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def extract_creation_date(s):
    """
    PrÃ³buje wyciÄ…gnÄ…Ä‡ datÄ™ z rÃ³Å¼nych formatÃ³w (ISO, listy, zaszumione stringi).
    Zwraca datetime|None
    """
    if s is None:
        return None
    if isinstance(s, list):
        # czasem w JSON-ie byÅ‚y listy dat; bierzemy pierwszÄ… sensownÄ…
        s = str(s[0]) if s else ""
    s = str(s)
    # Najpierw sprÃ³buj ISO
    try:
        # usuÅ„ strefÄ™ +00:00 jeÅ›li przeszkadza
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        pass
    # WyciÄ…gnij fragment daty YYYY-MM-DD przez regex
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            pass
    # Stare WHOIS-y czasem majÄ… YYYY
    m2 = re.search(r"(\d{4})", s)
    if m2:
        try:
            return datetime(int(m2.group(1)), 1, 1, tzinfo=timezone.utc)
        except Exception:
            pass
    return None

def tld_of(domain):
    parts = (domain or "").lower().split(".")
    return parts[-1] if parts else ""

def vendor_hint(entry):
    net = ((entry.get("ipwhois") or {}).get("network") or {})
    name = (net.get("name") or "").upper()
    return name

def best_country_guess(entry):
    # heurystyka: WHOIS country -> network country -> ASN CC -> 'US' jeÅ›li Google/Cloudflare/Akamai
    whois_cc = (entry.get("whois") or {}).get("country")
    net = ((entry.get("ipwhois") or {}).get("network") or {})
    net_country = net.get("country")
    asn_cc = (entry.get("ipwhois") or {}).get("asn_country_code")
    vend = vendor_hint(entry)
    if whois_cc: return whois_cc
    if net_country and net_country != "â€”": return net_country
    if asn_cc: return asn_cc
    if "GOOGLE" in vend or "CLOUDFLARE" in vend or "AKAMAI" in vend:
        return "US"
    return "?"

def risk_score(entry):
    """
    Zwraca (score:int 0..100, label:str)
    Zasady:
      +100 SAFE pin: jeÅ¼eli w SAFE_DOMAINS â†’ score max 20 i label SAFE
      bazowy 20 dla unknown
      +40 domena mÅ‚oda (<120 dni)
      +25 registrar na liÅ›cie podejrzanych (jeÅ›li nie w SAFE_DOMAINS)
      +20 CDN (Cloudflare/Akamai) + tld podejrzany i nieznany brand
      +30 sÅ‚owo-klucz w domenie
      ciÄ™cie do [0,100], progi: >=70 HIGH/SCAM, 40..69 WATCH, <40 SAFE
    """
    domain = (entry.get("domain") or "").lower()
    registrar = ((entry.get("whois") or {}).get("registrar") or "")
    vend = vendor_hint(entry)
    created_raw = (entry.get("whois") or {}).get("creation_date")
    created_dt = extract_creation_date(created_raw)
    now = datetime.now(timezone.utc)

    score = 20

    # znane i legit brandy
    if domain in SAFE_DOMAINS:
        score = 10
        return score, "SAFE"

    # mÅ‚oda domena
    if created_dt:
        age_days = (now - created_dt).days
        if age_days < 120:
            score += 40

    # registrar
    if registrar in SUSPICIOUS_REGISTRARS and domain not in SAFE_DOMAINS:
        # Alibaba bywa legit; mniejsza kara jeÅ›li to nie wyglÄ…da na scam (brak sÅ‚Ã³w-kluczy i niepodejrzany TLD)
        if "Alibaba Cloud" in registrar:
            score += 10
        else:
            score += 25

    # CDN + tld + nieznany brand
    tld = tld_of(domain)
    if (("CLOUDFLARE" in vend or "AKAMAI" in vend) and
        tld in SUSPICIOUS_TLDS and
        all(k not in domain for k in ("youtube", "tiktok", "shein", "zen.com", "telegram", "google"))):
        score += 20

    # sÅ‚owa kluczowe
    if any(k in domain for k in SUSPICIOUS_KEYWORDS):
        score += 30

    score = max(0, min(100, score))
    if score >= 70:
        label = "SCAM"
    elif score >= 40:
        label = "WATCH"
    else:
        label = "SAFE"
    return score, label

def build_bar_plot(country_counts):
    labels = list(country_counts.keys())
    values = [country_counts[k] for k in labels]

    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values)  # (narzucono w Twoim Å›rodowisku: bez custom kolorÃ³w)
    plt.title("Liczba domen wg kraju (heurystyka)")
    plt.xlabel("Kraj")
    plt.ylabel("Liczba")
    plt.tight_layout()
    plt.savefig(BAR_PNG, dpi=150)
    plt.close()

def color_for_label(label):
    # Kolory tÅ‚a w PDF
    if label == "SCAM":
        return colors.HexColor("#ffe5e5")  # jasny czerwony
    if label == "WATCH":
        return colors.HexColor("#fff9e6")  # jasny Å¼Ã³Å‚ty
    return colors.HexColor("#eaf7ea")      # jasny zielony

def main():
    if not os.path.exists(OUTDIR):
        os.makedirs(OUTDIR, exist_ok=True)

    whois_list = read_json_any_bom(WHOIS_JSON)
    if not isinstance(whois_list, list):
        raise RuntimeError("Plik whois_last.json powinien zawieraÄ‡ listÄ™ rekordÃ³w.")

    # wzbogacenie rekordÃ³w
    enriched = []
    country_counts = Counter()

    for r in whois_list:
        domain = r.get("domain")
        ip = r.get("ip")
        asn = (r.get("ipwhois") or {}).get("asn")
        registrar = (r.get("whois") or {}).get("registrar")
        created = (r.get("whois") or {}).get("creation_date")
        vend = vendor_hint(r)
        country = best_country_guess(r)
        sc, label = risk_score(r)

        country_counts[country] += 1

        enriched.append({
            "domain": domain,
            "ip": ip,
            "asn": asn,
            "registrar": registrar,
            "created": created,
            "vendor": vend,
            "country": country,
            "risk_score": sc,
            "risk_label": label
        })

    # wykres
    build_bar_plot(country_counts)

    # CSV z ryzykiem
    with open(CSV_RISK, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["domain","ip","asn","registrar","created","vendor","country","risk_score","risk_label"])
        for e in enriched:
            w.writerow([e["domain"], e["ip"], e["asn"], e["registrar"], e["created"],
                        e["vendor"], e["country"], e["risk_score"], e["risk_label"]])

    # PDF
    doc = SimpleDocTemplate(PDF_PATH, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Geo Visual Report z klasyfikacjÄ… ryzyka</b>", styles["Title"]))
    story.append(Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles["Normal"]))
    story.append(Spacer(1, 8))

    if os.path.exists(BAR_PNG):
        story.append(Image(BAR_PNG, width=480, height=270))
        story.append(Spacer(1, 12))

    # Tabela
    data = [["Domain","IP","ASN","Registrar","Created","Vendor","Country","Risk","Label"]]
    row_styles = []
    for i, e in enumerate(enriched, start=1):
        data.append([
            e["domain"], e["ip"] or "",
            e["asn"] or "",
            (e["registrar"] or "")[:40],
            (str(e["created"]) if e["created"] else "")[:22],
            (e["vendor"] or "")[:22],
            e["country"] or "",
            str(e["risk_score"]),
            e["risk_label"]
        ])
        # kolor wiersza
        bg = color_for_label(e["risk_label"])
        row_styles.append(("BACKGROUND", (0, i), (-1, i), bg))

    tbl = Table(data, repeatRows=1)
    ts = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("ALIGN", (2,0), (2,-1), "CENTER"),
        ("ALIGN", (6,0), (8,-1), "CENTER"),
        ("FONTSIZE", (0,1), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ] + row_styles)
    tbl.setStyle(ts)
    story.append(tbl)

    story.append(Spacer(1, 8))
    # Legenda
    legend = Paragraph(
        "<b>Legenda ryzyka:</b> "
        "<font color='#c0392b'>SCAM</font> â‰¥ 70, "
        "<font color='#f39c12'>WATCH</font> 40â€“69, "
        "<font color='#27ae60'>SAFE</font> &lt; 40. "
        "Heurystyka uwzglÄ™dnia wiek domeny, registrar, TLD, sÅ‚owa-klucze i dostawcÄ™ sieci (CDN).",
        styles["Normal"]
    )
    story.append(legend)

    doc.build(story)

    print(f"[OK] Wykres: {BAR_PNG}")
    print(f"[OK] CSV:    {CSV_RISK}")
    print(f"[OK] PDF:    {PDF_PATH}")

if __name__ == "__main__":
    main()




