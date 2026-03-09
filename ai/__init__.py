"""ai — all AI operations (Azure OpenAI) isolated here.

Shared Azure OpenAI client is initialised once in this module so every
sub-module imports it instead of creating its own.  Token tracking is
applied via the ``call_ai`` wrapper exported from this package.

The ``call_gemini`` name is kept as a backward-compatible alias.

12-Factor: API keys read from environment, never hard-coded.
"""

import base64
import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import AzureOpenAI
from PIL import Image

load_dotenv()

from constants import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    DATA_DIR,
    GEMINI_MODEL,
    PRICE_INPUT_PER_1K,
    PRICE_OUTPUT_PER_1K,
    TOKEN_RECORD_MAX,
)

logger = logging.getLogger(__name__)

# ── Initialise Azure OpenAI client ────────────────────────────────────────────

if not AZURE_OPENAI_API_KEY:
    logger.warning("AZURE_OPENAI_API_KEY not set — AI calls will fail")

_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)


# ── Image helpers ─────────────────────────────────────────────────────────────

def _pil_to_base64(img: Image.Image, fmt: str = "JPEG") -> str:
    """Convert a PIL Image to a base64-encoded data URI."""
    buf = io.BytesIO()
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}"
    return f"data:{mime};base64,{b64}"


def _bytes_to_base64_uri(image_bytes: bytes) -> str:
    """Convert raw image bytes to a base64 data URI."""
    img = Image.open(io.BytesIO(image_bytes))
    return _pil_to_base64(img)


# ── Backward-compatible wrappers ──────────────────────────────────────────────

class _ModelWrapper:
    """Drop-in replacement for the old GenerativeModel / google.genai wrapper.

    Used by claim_engine.py and main.py which still call
    ``gemini_model.generate_content([prompt, img, ...])``.
    """
    def generate_content(self, contents: list):
        """Mimic old Gemini generate_content by converting to Azure OpenAI chat."""
        messages_content: List[Dict] = []
        for item in contents:
            if isinstance(item, str):
                messages_content.append({"type": "text", "text": item})
            elif isinstance(item, Image.Image):
                data_uri = _pil_to_base64(item)
                messages_content.append({"type": "image_url", "image_url": {"url": data_uri}})
            else:
                # Unknown — stringify
                messages_content.append({"type": "text", "text": str(item)})

        response = _client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": messages_content}],
            max_tokens=4096,
        )

        # Wrap response to have .text and .usage_metadata compatible attributes
        return _CompatResponse(response)


class _CompatResponse:
    """Wraps Azure OpenAI response to look like old Gemini response."""
    def __init__(self, response):
        self._response = response
        self.text = response.choices[0].message.content or ""
        self.usage_metadata = _CompatUsage(response.usage)


class _CompatUsage:
    def __init__(self, usage):
        self.prompt_token_count = usage.prompt_tokens if usage else 0
        self.candidates_token_count = usage.completion_tokens if usage else 0


class _GenAICompat:
    """Backward-compatible genai namespace for analyse_damage.py file upload.

    Azure OpenAI does not support file uploads. PDF analysis is not available
    directly — the damage analysis will work without PDF when using Azure.
    """
    def upload_file(self, path, mime_type=None):
        logger.warning("upload_file not supported with Azure OpenAI — skipping PDF upload")
        return None

    def delete_file(self, name):
        pass


genai = _GenAICompat()


def get_model() -> _ModelWrapper:
    """Return the shared model instance (backward compat)."""
    return _model


_model = _ModelWrapper()


# ── Token tracking helper ─────────────────────────────────────────────────────

def _append_token_record(operation: str, input_tok: int, output_tok: int) -> None:
    """Append one JSONL record to {DATA_DIR}/token_records/YYYY-MM.jsonl."""
    import pathlib
    import constants as _c
    total = input_tok + output_tok
    cost = (input_tok / 1000 * PRICE_INPUT_PER_1K) + (output_tok / 1000 * PRICE_OUTPUT_PER_1K)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "model": AZURE_OPENAI_DEPLOYMENT,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "total_tokens": total,
        "cost_usd": round(cost, 6),
    }
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    token_dir = pathlib.Path(_c.DATA_DIR) / "token_records"
    token_dir.mkdir(parents=True, exist_ok=True)
    path = token_dir / f"{month}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.debug("Token record: op=%s total=%d cost=$%.6f", operation, total, cost)


# ── Public API ────────────────────────────────────────────────────────────────

def call_ai(operation: str, prompt: str, image: Optional[Image.Image] = None, images: Optional[List[Image.Image]] = None) -> str:
    """Call Azure OpenAI with a text prompt and optional image(s).

    Args:
        operation: human-readable name for the Admin dashboard.
        prompt:    text prompt.
        image:     optional single PIL Image.
        images:    optional list of PIL Images (for multi-image analysis).

    Returns:
        Response text string.
    """
    content: List[Dict] = [{"type": "text", "text": prompt}]
    
    if image is not None:
        data_uri = _pil_to_base64(image)
        content.append({"type": "image_url", "image_url": {"url": data_uri}})
        
    if images is not None:
        for img in images:
            data_uri = _pil_to_base64(img)
            content.append({"type": "image_url", "image_url": {"url": data_uri}})

    response = _client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "user", "content": content}],
        max_tokens=4096,
    )
    text = response.choices[0].message.content or ""

    try:
        usage = response.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0
        _append_token_record(operation, in_tok, out_tok)
    except Exception:  # noqa: BLE001
        logger.debug("Token metadata unavailable for op=%s", operation)

    return text


def call_gemini(operation: str, *contents: Any) -> str:
    """Backward-compatible alias — delegates to call_ai.

    Accepts: call_gemini("op", prompt_str, pil_image)
    """
    prompt_parts = []
    image = None
    for item in contents:
        if isinstance(item, str):
            prompt_parts.append(item)
        elif isinstance(item, Image.Image):
            image = item
        else:
            prompt_parts.append(str(item))
    prompt = "\n".join(prompt_parts)
    return call_ai(operation, prompt, image)
