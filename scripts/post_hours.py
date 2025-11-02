import json, collections, datetime, pytz
from pathlib import Path

# ---- Konfiguracja ----
OUTDIR = Path("scam_hunter_out")
TZ_LOCAL = pytz.timezone("Europe/Vienna")   # lokalna strefa czasu
FN = max(OUTDIR.glob("deep_report_*.json")) # ostatni plik z deep_scrape
print(f"[INFO] Analiza godzin publikacji w: {FN.name}")

# ---- Wczytanie danych ----
data = json.loads(FN.read_text(encoding="utf-8"))
hours = collections.Counter()
total_msgs = 0

# ---- Zliczanie godzin ----
for ch in data.get("channels", []):
    for msg in ch.get("samples", []):
        ts = msg.get("date")
        if not ts:
            continue
        try:
            dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            local_dt = dt.astimezone(TZ_LOCAL)
            hours[local_dt.hour] += 1
            total_msgs += 1
        except Exception:
            continue

# ---- Wyniki ----
print(f"[OK] Przetworzono {total_msgs} wiadomości.")
if not total_msgs:
    exit()

print("\n[Histogram godzin publikacji – czas lokalny (Europe/Vienna)]:\n")
for h in range(24):
    bar = "█" * (hours[h] // max(1, total_msgs // 50))  # skala 50 kroków
    print(f"{h:02d}:00 | {hours[h]:4d} {bar}")

# ---- Zapis CSV ----
csv_path = OUTDIR / "post_hours.csv"
with open(csv_path, "w", encoding="utf-8") as f:
    f.write("hour,count\n")
    for h in range(24):
        f.write(f"{h},{hours[h]}\n")
print(f"\n[OK] Zapisano histogram -> {csv_path}")
