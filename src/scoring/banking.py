from __future__ import annotations


BANK_KEYWORDS = [
# PL/DE/EN common scam bait
r"(podwoj.*(pieniadz|kase|profit|inwestycje))",
r"(gwarantowan[ey] zwrot|garantierte[rs]? gewinn|guaranteed return)",
r"(zadani(a|e) za lajki|like tasks|video tasks|pay per like)",
r"(USDT|TRC20|ERC20|recharge|top[- ]?up|binance agent)",
r"(skontaktuj .*WhatsApp|kontakt .*WhatsApp|WhatsApp:\s*\+?\d+)",
r"(krypto (mentor|doradca)|crypto mentor|VIP signals)",
r"(Revolut|Wise|gift card|voucher payment)",
]


BANK_DOMAINS_BAD_FRAGMENTS = [
# cheap clones / dodgy TLDs
".-binance", "-binance-", "binance-", "binanc[e0-9]", "-okx-", "bybit-",
".cash", ".gift", ".cfd", ".icu", ".ru", ".cn", ".top", ".xyz", ".zip",
]


WHATSAPP_RE = re.compile(r"https?://(wa\.me|api\.whatsapp\.com)/\d+|WhatsApp\s*[:=]\s*\+?\d+", re.I)
TG_RE = re.compile(r"t\.me/[A-Za-z0-9_]{3,}" , re.I)
USDT_RE = re.compile(r"USDT|TRC20|ERC20", re.I)




def score_text(text: str, url: str | None = None) -> Dict:
text_l = text.lower()
hits: List[ScoreHit] = []


for pat in BANK_KEYWORDS:
m = re.search(pat, text_l)
if m:
hits.append(ScoreHit(f"kw:{pat}", 20, m.group(0)[:120]))


if WHATSAPP_RE.search(text):
hits.append(ScoreHit("whatsapp", 20, "whatsapp contact"))
if TG_RE.search(text):
hits.append(ScoreHit("telegram", 10, "telegram handle"))
if USDT_RE.search(text):
hits.append(ScoreHit("usdt", 25, "USDT mention"))


if url:
ext = tldx(url)
domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
host = ".".join(part for part in [ext.subdomain, ext.domain, ext.suffix] if part)
for frag in BANK_DOMAINS_BAD_FRAGMENTS:
if frag in host.lower():
hits.append(ScoreHit("dodgy_tld", 15, host))


score = sum(h.weight for h in hits)
label = "banking_scam" if score >= 40 else ("suspicious" if score >= 25 else "unknown")
return {
"score": min(score, 100),
"label": label,
"hits": [h.__dict__ for h in hits],
}