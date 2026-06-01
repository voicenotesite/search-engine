import re

BLOCKED_CATEGORIES = [
    # Illegal porn
    r"child\s*(porn|abuse|exploit)",
    r"cp\b",
    r"underage\s*(sex|nude|porn)",
    r"snuff",
    r"rape",
    r"bestiality",
    r"incest\s*(porn|sex)",
    r"revenge\s*porn",
    r"non-consensual\s*porn",
    # Weapons trade (block buying/selling, allow informational)
    r"\b(buy|sell|purchase|order|trade)\s*(weapon|firearm|ammunition|ammo|explosive|bomb)\b",
    r"\b(weapon|firearm|ammunition|ammo|explosive|bomb)\s*(for\s*sale|to\s*buy|to\s*sell)\b",
    # Hitman and illegal services
    r"hitman",
    r"assassination",
    r"rent\s*(killer|hitman|assassin)",
    r"hire\s*(killer|hitman|assassin)",
    r"murder\s*(for\s*hire|contract)",
    r"torture\s*(service|for\s*hire)",
    r"human\s*trafficking",
    # Illegal drugs
    r"\b(buy|sell|purchase|order|trade)\s*(cocaine|heroin|meth|fentanyl|lsd|ecstasy|marijuana|cannabis)\b",
    r"\b(cocaine|heroin|meth|fentanyl|lsd|ecstasy|marijuana|cannabis)\s*(for\s*sale|to\s*buy|to\s*sell)\b",
    # Explosives and weapons manufacturing
    r"explosive\s*(device|making|recipe)",
    r"how\s*to\s*make\s*(bomb|explosive|weapon)",
    r"instructions\s*(for\s*making\s*(bomb|explosive|weapon))",
    # Hacking and illegal services
    r"hacker\s*(for\s*hire|service)",
    r"stolen\s*(credit|card|identity|data)",
    r"credit\s*card\s*dump",
    r"fake\s*(passport|id|document|license)",
    r"counterfeit\s*(money|currency|goods)",
    r"ransomware",
    r"malware\s*(creator|builder|for\s*hire)",
    r"ddos\s*(service|tool|for\s*hire)",
    # Other illegal
    r"illegal\s*(drug|weapon|firearm|porn|gambling)",
]

BLOCKED_KEYWORDS = [
    "cp", "loli", "pedo", "childporn",
    "snuff", "bestiality", "incest",
]

compiled_patterns = [re.compile(p, re.IGNORECASE) for p in BLOCKED_CATEGORIES]


def is_blocked(query: str) -> bool:
    for pattern in compiled_patterns:
        if pattern.search(query):
            return True
    for kw in BLOCKED_KEYWORDS:
        if kw.lower() in query.lower().split():
            return True
    return False


def filter_results(results: list[dict]) -> list[dict]:
    clean = []
    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')} {r.get('url', '')}"
        if not any(p.search(text) for p in compiled_patterns):
            clean.append(r)
    return clean
