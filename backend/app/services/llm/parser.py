from __future__ import annotations

import json


class LLMOutputParseError(ValueError):
    pass


def _strip_code_fences(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def extract_json_text(raw_text: str) -> str:
    cleaned = _strip_code_fences(raw_text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMOutputParseError("No JSON object found in model output")
    return cleaned[start : end + 1]


def parse_json_response(raw_text: str) -> dict:
    json_text = extract_json_text(raw_text)
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise LLMOutputParseError(f"Invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise LLMOutputParseError("Top-level JSON must be an object")

    return parsed
