import re
_BIC_RE = re.compile(r'\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?)\b')
def find_bics(text: str):
    return list(dict.fromkeys(m.group(1) for m in _BIC_RE.finditer(text.upper())))




