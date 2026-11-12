import json
from .config import DATA


def load(name, default):
    p = DATA / f"{name}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return default


def save(name, obj):
    p = DATA / f"{name}.json"
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
