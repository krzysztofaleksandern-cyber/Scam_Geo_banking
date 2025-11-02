from __future__ import annotations

# frazy wysokiego ryzyka (scam/krypto/bankowość/„bez ryzyka”/CTA)
RISK_KEYWORDS = [
    # bankowość / płatności
    r"\b(iban|blz|konto|überweisung|przelew|opłata|dopłata|dopłacisz|zwrot podatku)\b",
    r"\b(otp|tan|hasło jednorazowe|jednorazowy kod|sms code|verification code)\b",
    r"\b(bankowość|banking|sparkasse|raiffeisen|ing|mbank|pkobp|santander|revolut)\b",

    # krypto / inwestycje
    r"\b(krypto|bitcoin|btc|usdt|trx|binance|mining|copy\s*trading|signal group)\b",

    # obietnice / oszustwa marketingowe
    r"(0\%|100\%|be[zs] ryzyka|ohne risiko|garant.*zysk|garant.*gewinn|pewny zysk|sure profit)",
    r"\b(airdrop|bonus|giveaway|promocja|promotion|limited offer|tylko dziś|nur heute)\b",

    # komunikatory / przenoszenie rozmowy
    r"\b(whatsapp|telegram|t\.me|wa\.me|signal)\b",

    # podszycia / oficjalność
    r"\b(oficjalny|official|verifiziert|verified)\b",
]

# heurystyka reklam / CTA
AD_MARKERS = [
    r"\b(sponsorowane|sponsorowany|gesponsert|gesponserte|promoted|advertisement|ad)\b",
    r"\b(współpraca|paid\s*partnership|reklama|anzeige)\b",
    r"\b(kup teraz|buy now|zarejestruj się|sign up|claim|apply now|join now)\b",
    r"\b(link w opisie|link in bio|bio link|tap link)\b",
]

# waga fraz (opcjonalnie możesz podbić ważne)
WEIGHTS = {
    "iban": 12, "otp": 20, "tan": 20, "bitcoin": 15, "usdt": 15, "binance": 10,
    "telegram": 15, "t.me": 20, "whatsapp": 10, "dopłata": 15, "ohne risiko": 15,
    "garant": 15, "sure profit": 20, "sponsorowane": 5, "gesponsert": 5,
}

# dopuszczalne domeny/hosty w wynikach (opcjonalny filtr białej listy)
SAFE_HOST_HINTS = ["youtube.com", "tiktok.com", "facebook.com", "mbasic.facebook.com"]

DEFAULT_MIN_SCORE_WATCH = 20
DEFAULT_MIN_SCORE_MEDIUM = 35
DEFAULT_MIN_SCORE_HIGH = 60
