import re, yaml, pathlib

def load_brands(path:str):
    y = yaml.safe_load(pathlib.Path(path).read_text(encoding='utf-8'))
    brands=[]
    for b in y.get("brands", []):
        pats = [re.escape(p.lower()) for p in b.get("patterns",[])]
        brands.append({"name":b["name"], "patterns":pats, "trusted": set(b.get("domains_trusted",[]))})
    return brands

def match_brands(text:str, brands):
    t = text.lower()
    hits=[]
    for b in brands:
        for p in b["patterns"]:
            if p in t:
                hits.append(b["name"]); break
    return list(dict.fromkeys(hits))




