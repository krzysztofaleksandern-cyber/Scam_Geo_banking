from pathlib import Path
from scamgeo_banking.cli.scan import scan_web_targets
out_dir = Path("./out")
csv_path = scan_web_targets(["yt:UC_x5XG1OV2P6uZZ5FSM9Ttw"], out_dir)
print("CSV:", csv_path, "exists:", csv_path.exists())