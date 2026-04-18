import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Determine repository root (feature/outputs.py -> parents[1] == repo root)
REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_OUTPUTS = REPO_ROOT / "outputs"


def ensure_outputs_dir(base: Optional[Path] = None) -> Path:
    base = base or BASE_OUTPUTS
    base.mkdir(parents=True, exist_ok=True)
    return base


def _next_version_index(base: Optional[Path] = None) -> int:
    base = ensure_outputs_dir(base)
    max_i = 0
    for p in base.iterdir():
        if not p.is_dir():
            continue
        name = p.name
        if not name.startswith("version_"):
            continue
        try:
            i = int(name.split("_", 1)[1])
            if i > max_i:
                max_i = i
        except Exception:
            continue
    return max_i + 1


def next_version_dir(base: Optional[Path] = None) -> Path:
    base = ensure_outputs_dir(base)
    idx = _next_version_index(base)
    vdir = base / f"version_{idx}"
    vdir.mkdir(parents=True, exist_ok=False)
    return vdir


def save_attempt(version_dir: Path, attempt_index: int, raw_text: str) -> Path:
    p = version_dir / f"raw_attempt_{attempt_index}.txt"
    p.write_text(raw_text or "", encoding="utf-8")
    return p


def save_parsed(version_dir: Path, parsed_obj: Any) -> Path:
    p = version_dir / "parsed.json"
    with p.open("w", encoding="utf-8") as f:
        json.dump(parsed_obj, f, ensure_ascii=False, indent=2)
    return p


def save_meta(version_dir: Path, meta: Dict[str, Any]) -> Path:
    p = version_dir / "meta.json"
    meta_out = {"timestamp": time.time()}
    meta_out.update(meta or {})
    with p.open("w", encoding="utf-8") as f:
        json.dump(meta_out, f, ensure_ascii=False, indent=2)
    return p
