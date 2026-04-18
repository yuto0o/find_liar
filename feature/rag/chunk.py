import os


def load_statements(path: str):
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    if not os.path.exists(path):
        raise FileNotFoundError(f"file not found: {path}")
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines
