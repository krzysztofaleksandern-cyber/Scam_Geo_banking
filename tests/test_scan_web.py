from pathlib import Path
import csv, tempfile

# ✅ ABSOLUTNY import z kodu produkcyjnego
from scamgeo_banking.cli.scan import scan_web_targets

def _read(p: Path):
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def test_scan_web_dedup_and_overwrite():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        scan_web_targets(["yt:UC_x5XG1OV2P6uZZ5FSM9Ttw"], out)
        p = out / "webscan_scored.csv"
        rows1 = _read(p)
        assert len(rows1) == 1
        # drugi przebieg nie powinien mnożyć rekordów
        scan_web_targets(["yt:UC_x5XG1OV2P6uZZ5FSM9Ttw"], out)
        rows2 = _read(p)
        assert len(rows2) == 1
