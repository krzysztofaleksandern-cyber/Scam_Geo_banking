from __future__ import annotations
import argparse, json, logging, os, sys
from pathlib import Path
# --- Force UTF-8 stdio on Windows ---
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
# ------------------------------------
