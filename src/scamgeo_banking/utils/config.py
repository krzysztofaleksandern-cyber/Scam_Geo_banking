import json, os
from pathlib import Path
def load_config(path: str | None):
    if not path: return {}
    p = Path(path)
    if not p.exists(): return {}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

