

def hexToMACString(s: str):
    s = s.upper()
    return ":".join(s[i:i+2] for i in range(0, len(s), 2))