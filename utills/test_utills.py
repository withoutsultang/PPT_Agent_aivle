import re

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def split_sents(t: str):
    import re
    parts = re.split(r'([\.?!])', t)
    merged = []
    for i in range(0, len(parts)-1, 2):
        sent = (parts[i] + parts[i+1]).strip()
        if sent:
            merged.append(sent)
    if len(parts) % 2 == 1 and parts[-1].strip():
        merged.append(parts[-1].strip())
    return [s for s in merged if s]
