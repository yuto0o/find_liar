import json
import logging
import re
import time
from typing import Any, Dict, Optional

from feature.metrics import metrics

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        # import lazily to avoid heavy initialization at import time
        from llama_cpp import Llama

        from feature.config import get_model_path

        model_path = get_model_path()
        _llm = Llama(model_path=model_path, n_gpu_layers=40, n_ctx=4096)
    return _llm


def _extract_json_from_fenced(raw: str) -> Optional[str]:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.S | re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"~~~(?:json)?\s*(\{.*?\})\s*~~~", raw, flags=re.S | re.I)
    if m:
        return m.group(1).strip()
    return None


def _extract_json_by_brace_matching(raw: str) -> Optional[str]:
    starts = [m.start() for m in re.finditer(r"\{", raw)]
    for start in starts:
        depth = 0
        for i in range(start, len(raw)):
            c = raw[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidate = raw[start : i + 1]
                    try:
                        json.loads(candidate)
                        return candidate.strip()
                    except Exception:
                        break
    return None


def generate(
    prompt: str,
    retries: int = 2,
    backoff: float = 1.0,
    require_json: bool = False,
    json_max_attempts: int = 2,
    **kwargs,
) -> str:
    """Generate text from the model with retry/backoff.

    If `require_json=True`, the function will try to return a valid JSON string
    (extracted from fences or by brace matching). On parse failure it will
    re-query the model with stricter JSON settings up to `json_max_attempts`.
    """
    from feature.config import (
        DEFAULT_GENERATION_SETTINGS,
        STRICT_JSON_GENERATION_SETTINGS,
    )

    settings: Dict[str, Any] = DEFAULT_GENERATION_SETTINGS.copy()
    settings.update(kwargs)

    call_kwargs: Dict[str, Any] = {
        "max_tokens": settings.get("max_tokens", 4096),
        "temperature": settings.get("temperature", 0.0),
        "top_p": settings.get("top_p", 1.0),
    }
    if settings.get("stop") is not None:
        call_kwargs["stop"] = settings.get("stop")

    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        metrics.inc("generate.calls")
        start = time.perf_counter()
        try:
            llm = _get_llm()
            res = llm(prompt, **call_kwargs)
            try:
                text = res["choices"][0].get("text", "")
            except Exception:
                text = str(res)
            text = text.strip()

            duration = time.perf_counter() - start
            metrics.record_time("generate.total_seconds", duration)
            metrics.add("generate.total_time_ms", int(duration * 1000))

            logger.info(
                "generate: attempt=%d require_json=%s text_len=%d",
                attempt + 1,
                require_json,
                len(text),
            )

            if not require_json:
                metrics.inc("generate.plain.success")
                return text

            # try to extract JSON from the model output
            json_str = _extract_json_from_fenced(
                text
            ) or _extract_json_by_brace_matching(text)
            if json_str:
                try:
                    json.loads(json_str)
                    metrics.inc("generate.json.success")
                    return json_str.strip()
                except Exception:
                    logger.debug(
                        "generate: extracted JSON invalid, will attempt repair"
                    )

            # attempt repair/re-formatting using stricter JSON settings
            repair_source = text
            for j in range(json_max_attempts):
                metrics.inc("generate.json.repair.attempts")
                repair_prompt = (
                    "先ほどの出力は有効なJSONではありませんでした。元の出力を示します。\n\n"
                    + repair_source
                    + "\n\n上記を『純粋なJSONのみ』で、余計な説明を含めずに書き直してください。JSONのみを返してください。"
                )

                repair_settings = STRICT_JSON_GENERATION_SETTINGS.copy()
                # allow caller overrides to still apply
                repair_settings.update(kwargs)

                repair_call_kwargs: Dict[str, Any] = {
                    "max_tokens": repair_settings.get("max_tokens", 4096),
                    "temperature": repair_settings.get("temperature", 0.0),
                    "top_p": repair_settings.get("top_p", 1.0),
                }
                if repair_settings.get("stop") is not None:
                    repair_call_kwargs["stop"] = repair_settings.get("stop")

                res2 = llm(repair_prompt, **repair_call_kwargs)
                try:
                    repaired_text = res2["choices"][0].get("text", "")
                except Exception:
                    repaired_text = str(res2)
                repaired_text = repaired_text.strip()

                logger.info(
                    "generate: repair attempt %d got len=%d", j + 1, len(repaired_text)
                )
                json_str2 = _extract_json_from_fenced(
                    repaired_text
                ) or _extract_json_by_brace_matching(repaired_text)
                if json_str2:
                    try:
                        json.loads(json_str2)
                        metrics.inc("generate.json.repair.success")
                        return json_str2.strip()
                    except Exception:
                        logger.debug("generate: repaired JSON invalid; continue")
                        repair_source = repaired_text
                        continue
                # if no JSON found, use repaired_text as next source and loop
                repair_source = repaired_text

            # all repair attempts failed, return the last text we have
            metrics.inc("generate.json.repair.failures")
            logger.warning(
                "generate: require_json failed after repairs; returning raw text"
            )
            return text

        except Exception as e:
            metrics.inc("generate.errors")
            logger.exception("LLM generate failed on attempt %d", attempt + 1)
            last_exc = e
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise

    if last_exc:
        raise last_exc
    return ""
