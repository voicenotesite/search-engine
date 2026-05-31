import re

BLOCKED_CATEGORIES = [
    r"child\s*(porn|abuse|exploit)",
    r"cp\b",
    r"underage\s*(sex|nude|porn)",
    r"snuff",
    r"murder\s*(video|for\s*sale)",
    r"hitman",
    r"assassination",
    r"torture",
    r"human\s*trafficking",
    r"illegal\s*(drug|weapon|firearm)",
    r"explosive\s*(device|making)",
    r"hacker\s*(for\s*hire|service)",
    r"stolen\s*(credit|card|identity)",
    r"credit\s*card\s*dump",
    r"fake\s*(passport|id|document)",
    r"counterfeit",
    r"ransomware",
    r"malware\s*(creator|builder)",
    r"ddos\s*(service|tool)",
]

BLOCKED_KEYWORDS = [
    "cp", "loli", "pedo", "childporn",
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
