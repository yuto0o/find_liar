import os
from typing import Optional

from huggingface_hub import hf_hub_download

# Model repo/filename are defined here; actual download happens on demand via `get_model_path()`
MODEL_REPO = "alfredplpl/llm-jp-4-8b-thinking-gguf"
MODEL_FILENAME = "llm-jp-4-8B-thinking-Q4_K_M.gguf"


def get_model_path(download: bool = True) -> str:
    """Return a path to the model file.

    Priority:
    - If environment variable `MODEL_PATH` is set and exists, use it.
    - If `download=True`, download from HF hub and return path.
    - Otherwise raise RuntimeError.
    """
    env_path = os.environ.get("MODEL_PATH")
    if env_path:
        if os.path.exists(env_path):
            return env_path
        # If env var points to a non-existent file, raise early
        raise RuntimeError(f"MODEL_PATH is set but does not exist: {env_path}")
    if download:
        return hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILENAME)
    raise RuntimeError(
        "Model path not set and download disabled. Set MODEL_PATH env var or allow download."
    )


# Default generation settings (can be overridden per-call)
DEFAULT_GENERATION_SETTINGS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 4096,
    "stop": None,
}

# Strict settings used when we require machine-parseable JSON outputs.
STRICT_JSON_GENERATION_SETTINGS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 4096,
    # Stop on triple-backtick or double-newline to reduce trailing commentary
    "stop": ["```", "\n\n"],
}


# Small JSON prompt examples. We relax to allow an optional `explanation` field
# where the model may place human-readable reasoning or commentary. The parser
# will still prefer machine-parseable JSON in `edges` but will record `explanation`
# for analysis when present.
JSON_OUTPUT_INSTRUCTIONS = (
    "出力はJSONで返してください。必須フィールドは `edges` (配列) です。"
    " 任意で `explanation` に短い説明や思考過程を入れてください。\n"
    '良い例:\n{\n  "edges": [{"source": "A", "target": "B", "relation": "supports"}],\n  "explanation": "AがBを支持しているため"\n}\n'
    "悪い例: JSONを壊すような前置きやコードフェンスを混ぜること。\n"
)


EMBED_MODEL = "intfloat/multilingual-e5-base"

TOP_K = 5
