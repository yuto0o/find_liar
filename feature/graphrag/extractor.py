import json
import logging
import re
import time
from typing import Optional

from feature.graphrag.schema import GraphOutput
from feature.metrics import metrics
from feature.outputs import next_version_dir, save_attempt, save_meta, save_parsed

logger = logging.getLogger(__name__)


def _normalize_relation(rel: Optional[str]) -> str:
    """Normalize relation strings (Japanese/English) to canonical literals.

    Returns one of: 'supports', 'contradicts', 'same', or the original string
    if no mapping is found.
    """
    if rel is None:
        return ""
    if not isinstance(rel, str):
        rel = str(rel)
    r = rel.strip().lower()
    mapping = {
        "支持": "supports",
        "支持する": "supports",
        "賛成": "supports",
        "support": "supports",
        "supports": "supports",
        "矛盾": "contradicts",
        "矛盾する": "contradicts",
        "反対": "contradicts",
        "contradict": "contradicts",
        "contradicts": "contradicts",
        "同じ": "same",
        "一致": "same",
        "同様": "same",
        "same": "same",
    }
    if r in mapping:
        return mapping[r]
    # fallback heuristics
    if "支持" in rel or "賛成" in rel or "support" in r:
        return "supports"
    if "矛盾" in rel or "反対" in rel or "contrad" in r:
        return "contradicts"
    if "同" in rel or "一致" in rel or "same" in r:
        return "same"
    return rel


def _extract_json_from_fenced(raw: str) -> Optional[str]:
    # Try triple-backtick fences first (```json ... ``` or ``` ... ```)
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.S | re.I)
    if m:
        return m.group(1).strip()
    # Try triple-tilde fences
    m = re.search(r"~~~(?:json)?\s*(\{.*?\})\s*~~~", raw, flags=re.S | re.I)
    if m:
        return m.group(1).strip()
    return None


def _extract_json_by_brace_matching(raw: str) -> Optional[str]:
    # Find first balanced JSON object using a stack-based scan
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
                    # Quick sanity: candidate should start with { and end with }
                    try:
                        json.loads(candidate)
                        return candidate.strip()
                    except Exception:
                        # not valid JSON, continue searching for other starts
                        break
    return None


def _parse_json_flex(json_str: str):
    """Try to parse JSON flexibly: normal loads, then raw_decode to extract first JSON object.

    Returns parsed object on success or raises the original exception.
    """
    try:
        return json.loads(json_str)
    except Exception:
        # try to decode a prefix JSON if there is extra trailing data
        try:
            decoder = json.JSONDecoder()
            obj, idx = decoder.raw_decode(json_str)
            return obj
        except Exception:
            raise


def extract_graph(text: str):
    prompt = f"""
  以下の証言から人物間の関係を抽出してください。

  出力は必ずJSON形式：
  {{
    "edges": [
    {{"source": "A", "target": "B", "relation": "contradicts"}}
    ]
  }}

  relationは以下のみ：
  - supports
  - contradicts
  - same

  出力は"純粋なJSON"のみを返してください。余計な説明やコードフェンスを含めないでください。

  証言：
  {text}
  """
    # append stronger JSON-only instruction examples from config
    from feature.config import JSON_OUTPUT_INSTRUCTIONS

    prompt = JSON_OUTPUT_INSTRUCTIONS + "\n" + prompt

    # create a version directory to save raw outputs / parsed results for offline analysis
    version_dir = next_version_dir()
    attempt_idx = 0

    # import generate lazily to avoid heavy model initialization on module import
    from feature.llm.llama import generate

    # ask the LLM to return pure JSON; let generate attempt repairs if needed
    raw = generate(prompt, require_json=True, json_max_attempts=5)
    attempt_idx += 1
    try:
        save_attempt(version_dir, attempt_idx, str(raw))
    except Exception:
        logger.exception("Failed to save raw attempt")
    if raw is None:
        logger.error("LLM returned None")
        metrics.inc("extractor.llm_none")
        return []
    raw = str(raw)

    # 1) fenced code block extraction
    json_str = _extract_json_from_fenced(raw)

    # 2) brace matching extraction
    if not json_str:
        json_str = _extract_json_by_brace_matching(raw)

    def _attempt_repair_and_parse(prev_raw: str):
        from feature.llm.llama import generate

        nonlocal attempt_idx
        for attempt in range(2):
            repair_prompt = f"""
      先ほどの出力は有効なJSONではありませんでした。以下に元の出力を示します。

      {prev_raw}

      上記を『純粋なJSONのみ』で、余計な説明を含めずに書き直してください。JSONのみを返してください。
      """
            try:
                repaired_raw = generate(
                    repair_prompt, temperature=0.0, max_tokens=4096, retries=2
                )
                attempt_idx += 1
                try:
                    save_attempt(version_dir, attempt_idx, str(repaired_raw))
                except Exception:
                    logger.exception("Failed to save repaired attempt")
            except Exception as ge:
                logger.exception("Repair generate failed")
                metrics.inc("extractor.repair.generate_failed")
                continue

            json_str2 = _extract_json_from_fenced(
                repaired_raw
            ) or _extract_json_by_brace_matching(repaired_raw)
            if not json_str2:
                logger.warning("No JSON found in repaired output")
                metrics.inc("extractor.repair.no_json")
                continue
            try:
                data = _parse_json_flex(json_str2)
            except Exception:
                logger.exception("Repaired JSON parse failed (flex)")
                metrics.inc("extractor.repair.parse_failed")
                logger.debug("Repaired raw:\n%s", repaired_raw)
                continue

            # Normalize single-edge dicts into edges list
            if isinstance(data, dict) and "edges" not in data:
                # case: single edge as dict {'source':..,'target':..,'relation':..}
                if all(k in data for k in ("source", "target")):
                    data = {"edges": [data]}
                else:
                    edges_list = []
                    for k, v in data.items():
                        m = re.match(r"^\s*(.+?)と(.+?)の関係\s*$", k)
                        if m:
                            src = m.group(1).strip()
                            tgt = m.group(2).strip()
                            raw_rel = v if isinstance(v, str) else str(v)
                            rel = _normalize_relation(raw_rel)
                            edges_list.append(
                                {"source": src, "target": tgt, "relation": rel}
                            )
                    if edges_list:
                        data = {"edges": edges_list}

            # If top-level is a list of edge-like dicts, wrap
            if isinstance(data, list):
                if data and isinstance(data[0], dict) and "source" in data[0]:
                    data = {"edges": data}

            # normalize relation strings to canonical literals
            if isinstance(data, dict) and "edges" in data:
                for e in data["edges"]:
                    if "relation" in e:
                        try:
                            e["relation"] = _normalize_relation(e["relation"])
                        except Exception:
                            pass

            # Extract explanation from repaired_raw if not present
            if isinstance(data, dict) and not data.get("explanation"):
                try:
                    rem = repaired_raw.replace(json_str2, "", 1).strip()
                    if rem:
                        data["explanation"] = rem
                except Exception:
                    pass

            try:
                parsed = GraphOutput(**data)
                metrics.inc("extractor.repair.parse_success")
                # save parsed + meta
                try:
                    save_parsed(version_dir, data)
                    save_meta(
                        version_dir,
                        {"attempts": attempt_idx, "success": True, "repaired": True},
                    )
                except Exception:
                    logger.exception(
                        "Failed to save parsed/metadata for repaired output"
                    )
                return parsed.edges
            except Exception:
                logger.exception("Repaired parse failed (validation)")
                metrics.inc("extractor.repair.parse_failed")
                logger.debug("Repaired raw:\n%s", repaired_raw)
                continue
        return None

    if not json_str:
        logger.warning(
            "No JSON found in model output (first-pass). Trunc: %s", raw[:200]
        )
        metrics.inc("extractor.no_json_found")
        repaired = _attempt_repair_and_parse(raw)
        if repaired is not None:
            metrics.inc("extractor.repaired_success")
            return repaired
        logger.error(
            "All parse/repair attempts failed. Raw model output truncated: %s",
            raw[:200],
        )
        metrics.inc("extractor.parse_failures")
        try:
            save_meta(
                version_dir,
                {"attempts": attempt_idx, "success": False, "error": "no_json_found"},
            )
        except Exception:
            logger.exception("Failed to save meta on overall failure")
        return []

    try:
        try:
            data = _parse_json_flex(json_str)
        except Exception:
            logger.exception("Initial JSON parse failed (flex)")
            raise

        # Normalize shapes
        if isinstance(data, dict) and "edges" not in data:
            # single-edge dict
            if all(k in data for k in ("source", "target")):
                data = {"edges": [data]}
            else:
                edges_list = []
                for k, v in data.items():
                    m = re.match(r"^\s*(.+?)と(.+?)の関係\s*$", k)
                    if m:
                        src = m.group(1).strip()
                        tgt = m.group(2).strip()
                        rel = v if isinstance(v, str) else str(v)
                        edges_list.append(
                            {"source": src, "target": tgt, "relation": rel}
                        )
                if edges_list:
                    data = {"edges": edges_list}

        if isinstance(data, list):
            if data and isinstance(data[0], dict) and "source" in data[0]:
                data = {"edges": data}

        # Extract explanation from raw if not present
        if isinstance(data, dict) and not data.get("explanation"):
            try:
                rem = raw.replace(json_str, "", 1).strip()
                if rem:
                    data["explanation"] = rem
            except Exception:
                pass

        parsed = GraphOutput(**data)
        metrics.inc("extractor.parse_success")
        try:
            save_parsed(version_dir, data)
            save_meta(
                version_dir,
                {"attempts": attempt_idx, "success": True, "repaired": False},
            )
        except Exception:
            logger.exception("Failed to save parsed/metadata for initial parse")
        return parsed.edges
    except Exception:
        logger.exception("Initial parse failed")
        metrics.inc("extractor.parse_exception")
        repaired = _attempt_repair_and_parse(raw)
        if repaired is not None:
            metrics.inc("extractor.repaired_success")
            return repaired
        logger.error(
            "All parse/repair attempts failed. Raw model output truncated: %s",
            raw[:200],
        )
        metrics.inc("extractor.parse_failures")
        try:
            save_meta(
                version_dir,
                {
                    "attempts": attempt_idx,
                    "success": False,
                    "error": "initial_parse_exception",
                },
            )
        except Exception:
            logger.exception("Failed to save meta on exception")
        return []
