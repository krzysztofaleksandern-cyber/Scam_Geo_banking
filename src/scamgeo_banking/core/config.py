import os, json

def load_json(path):
    if path and os.path.exists(path):
        with open(path,'r',encoding='utf-8') as f: return json.load(f)
    return {}

def env(name, default=None): 
    return os.environ.get(name, default)




