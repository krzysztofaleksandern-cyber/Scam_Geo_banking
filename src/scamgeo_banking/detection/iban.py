import re

_IBAN_RE = re.compile(r'\b([A-Z]{2}\d{2}[A-Z0-9]{1,30})\b')
_LENGTH = {"AT":20, "DE":22, "CH":21}

def _iban_clean(s:str)->str:
    return re.sub(r'[^A-Z0-9]', '', s.upper())

def _mod97(numeric: str) -> int:
    return int(numeric) % 97

def _to_numeric(iban: str) -> str:
    return ''.join(str(ord(c)-55) if c.isalpha() else c for c in iban)

def validate_iban(iban: str) -> bool:
    i = _iban_clean(iban)
    if len(i) < 4: return False
    cc = i[:2]
    if cc not in _LENGTH or len(i) != _LENGTH[cc]: return False
    rearr = i[4:] + i[:4]
    return _mod97(_to_numeric(rearr)) == 1

def find_ibans(text: str):
    out=[]
    for m in _IBAN_RE.finditer(text.upper()):
        cand = m.group(1)
        try:
            if validate_iban(cand):
                out.append(cand)
        except Exception:
            pass
    return list(dict.fromkeys(out))




