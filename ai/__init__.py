"""ai — all AI operations (Gemini) isolated here.

Shared Gemini client is initialised once in this module so every sub-module
imports it instead of creating its own.  Token tracking is applied via the
``_call_gemini`` wrapper exported from this package.

12-Factor: API key read from environment (GEMINI_API_KEY), never hard-coded.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import google.generativeai as genai

from constants import (
    DATA_DIR,
    GEMINI_MODEL,
    PRICE_INPUT_PER_1K,
    PRICE_OUTPUT_PER_1K,
    TOKEN_RECORD_MAX,
)

logger = logging.getLogger(__name__)

# ── Initialise Gemini client ──────────────────────────────────────────────────
_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise EnvironmentError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=_api_key)
_model = genai.GenerativeModel(model_name=GEMINI_MODEL)


# ── Token tracking helper ─────────────────────────────────────────────────────

def _append_token_record(operation: str, input_tok: int, output_tok: int) -> None:
    """Append one JSONL record to /data/token_records/YYYY-MM.jsonl."""
    import pathlib
    total = input_tok + output_tok
    cost = (input_tok / 1000 * PRICE_INPUT_PER_1K) + (output_tok / 1000 * PRICE_OUTPUT_PER_1K)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "model": GEMINI_MODEL,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "total_tokens": total,
        "cost_usd": round(cost, 6),
    }
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    token_dir = pathlib.Path(DATA_DIR) / "token_records"
    token_dir.mkdir(parents=True, exist_ok=True)
    path = token_dir / f"{month}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.debug("Token record: op=%s total=%d cost=$%.6f", operation, total, cost)


def call_gemini(operation: str, *contents: Any) -> str:
    """Call Gemini, record token usage, and return response text.

    Args:
        operation: human-readable name for the Admin dashboard
        *contents: positional args forwarded to ``generate_content()``

    Returns:
        Response text string.

    Raises:
        Exception: propagates Gemini exceptions for callers to handle.
    """
    response = _model.generate_content(list(contents))
    try:
        in_tok = response.usage_metadata.prompt_token_count or 0
        out_tok = response.usage_metadata.candidates_token_count or 0
        _append_token_record(operation, in_tok, out_tok)
    except Exception:  # noqa: BLE001
        logger.debug("Token metadata unavailable for op=%s", operation)
    return response.text


def get_model() -> genai.GenerativeModel:
    """Return the shared GenerativeModel instance."""
    return _model
