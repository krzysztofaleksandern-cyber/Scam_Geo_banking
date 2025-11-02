import sys
from pathlib import Path

# root projektu = katalog wyżej niż "tests"
root = Path(__file__).resolve().parents[1]
src = root / "src"

# dopnij src/ do sys.path (jeśli nie ma)
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
