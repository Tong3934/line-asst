"""
conftest.py
===========
Shared pytest fixtures for the LINE Insurance Claim Bot integration tests.

Key fixtures
------------
app_client          : TestClient wrapping the FastAPI app with all external
                      dependencies (LINE API, Gemini AI, file I/O) mocked.
clean_sessions      : Resets user_sessions between tests.
tmp_data_dir        : Temporary directory that replaces DATA_DIR for each test.
mock_line_api       : Patches linebot MessagingApi so no real HTTP calls go out.
mock_gemini         : Patches all Gemini AI calls.
mock_image_download : Patches httpx so image downloads return dummy bytes.
"""

import json
import os
import sys
import types
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── make the project root importable ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_data import (
    DUMMY_JPEG_BYTES,
    MOCK_CHANNEL_ACCESS_TOKEN,
    MOCK_CHANNEL_SECRET,
    OCR_RESPONSE_ID_CARD,
    OCR_RESPONSE_UNKNOWN,
    CATEGORISE_DRIVING_LICENSE,
    EXTRACTED_DRIVING_LICENSE,
    DAMAGE_ANALYSIS_ELIGIBLE,
    CD_POLICY_ACTIVE_CLASS1,
)


# ─────────────────────────────────────────────────────────────────────────────
# Environment setup (must happen before app import)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _set_env_vars(tmp_path_factory):
    """Inject fake credentials before any module touches os.environ."""
    tmp_data = tmp_path_factory.mktemp("data")
    env_overrides = {
        "LINE_CHANNEL_ACCESS_TOKEN": MOCK_CHANNEL_ACCESS_TOKEN,
        "LINE_CHANNEL_SECRET":       MOCK_CHANNEL_SECRET,
        "GEMINI_API_KEY":            "fake_gemini_key_for_tests",
        "DATA_DIR":                  str(tmp_data),
        "LINE_API_HOST":             "http://localhost:8001",
        "LINE_DATA_API_HOST":        "http://localhost:8001",
    }
    with patch.dict(os.environ, env_overrides):
        yield


# ─────────────────────────────────────────────────────────────────────────────
# Stub-out Google Generative AI before main.py is imported
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _stub_genai(_set_env_vars):
    """
    Replace `google.generativeai` with a thin MagicMock so main.py can be
    imported without real credentials.
    """
    genai_stub = MagicMock()
    genai_stub.configure = MagicMock()
    genai_stub.GenerativeModel.return_value = MagicMock()
    sys.modules["google"] = MagicMock()
    sys.modules["google.generativeai"] = genai_stub
    yield genai_stub


# ─────────────────────────────────────────────────────────────────────────────
# Import app *after* env + genai stub are in place
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def fastapi_app(_stub_genai, _set_env_vars):
    """Import and return the FastAPI app instance (once per session)."""
    import main as m
    return m.app


@pytest.fixture(scope="session")
def main_module(_stub_genai, _set_env_vars):
    """Return the main module so tests can access user_sessions, etc."""
    import main as m
    return m


# ─────────────────────────────────────────────────────────────────────────────
# TestClient
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def app_client(fastapi_app, mock_line_api, mock_gemini, mock_image_download):
    """
    FastAPI TestClient with all side-effecting dependencies mocked.
    Each test gets a fresh client (function scope).
    """
    with TestClient(fastapi_app, raise_server_exceptions=False) as client:
        yield client


# ─────────────────────────────────────────────────────────────────────────────
# Session isolation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_sessions(main_module):
    """Clear user_sessions before and after every test."""
    main_module.user_sessions.clear()
    yield
    main_module.user_sessions.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Temporary DATA_DIR
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_data_dir(tmp_path):
    """
    A fresh temp directory acting as DATA_DIR.
    Creates the standard sub-folders expected by storage helpers.
    """
    claims_dir = tmp_path / "claims"
    claims_dir.mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "token_records").mkdir()
    # Initialise sequence file
    seq = tmp_path / "sequence.json"
    seq.write_text(json.dumps({"CD": 0, "H": 0}))
    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Mock: LINE Messaging API  (no real HTTP to LINE)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_line_api():
    """
    Patch ApiClient (context manager) and MessagingApi so reply_message /
    push_message are no-ops.  Tests can inspect `.call_args_list` on the mock.
    """
    mock_api = MagicMock()
    mock_api.reply_message = MagicMock(return_value=None)
    mock_api.push_message  = MagicMock(return_value=None)

    # ApiClient is used as `with ApiClient(config) as api_client:`
    # so we need it to behave as a context manager returning a dummy
    mock_api_client_instance = MagicMock()
    mock_api_client_instance.__enter__ = MagicMock(return_value=mock_api_client_instance)
    mock_api_client_instance.__exit__  = MagicMock(return_value=False)
    MockApiClient = MagicMock(return_value=mock_api_client_instance)

    with patch("linebot.v3.messaging.ApiClient",    MockApiClient), \
         patch("main.ApiClient",                    MockApiClient), \
         patch("linebot.v3.messaging.MessagingApi", return_value=mock_api), \
         patch("main.MessagingApi",                 return_value=mock_api):
        yield mock_api


# ─────────────────────────────────────────────────────────────────────────────
# Mock: Gemini AI calls
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_gemini():
    """
    Patch the shared Gemini model in the ai package so all AI calls
    return configurable fake responses.

    In v2.0 the model lives at ai._model (used via ai.call_gemini).
    Exposes `.generate_content` — tests can reassign `.return_value` as needed.
    """
    # Default OCR response: returns a valid JSON string for an ID card
    default_ocr_text = json.dumps(OCR_RESPONSE_ID_CARD)
    mock_response = MagicMock()
    mock_response.text = default_ocr_text

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch("ai._model", mock_model), \
         patch("config.gemini_model", mock_model):
        yield mock_model


# ─────────────────────────────────────────────────────────────────────────────
# Mock: httpx image download
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_image_download():
    """
    Intercept httpx.Client.get so image download from LINE Data API returns
    DUMMY_JPEG_BYTES instead of making a real network call.
    """
    mock_response = MagicMock()
    mock_response.content = DUMMY_JPEG_BYTES
    mock_response.raise_for_status = MagicMock(return_value=None)

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__  = MagicMock(return_value=False)
    mock_client.get       = MagicMock(return_value=mock_response)

    with patch("httpx.Client", return_value=mock_client):
        yield mock_client


# ─────────────────────────────────────────────────────────────────────────────
# Mock: mock_data policy lookups
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_policy_lookup():
    """
    Patch mock_data search functions so tests control what policies are returned
    without touching the real mock_data.py.

    In v2.0 the lookups are done inside handlers.identity (not main).
    Yields a dict with keys: `by_cid`, `by_plate`, `by_name` — each is a
    MagicMock whose `.return_value` can be adjusted per test.
    """
    # In the current main.py the lookups are imported directly from mock_data
    with patch("main.search_policies_by_cid",   return_value=[CD_POLICY_ACTIVE_CLASS1]) as p_cid, \
         patch("main.search_policies_by_plate",  return_value=CD_POLICY_ACTIVE_CLASS1)  as p_plate, \
         patch("main.search_policies_by_name",   return_value=[CD_POLICY_ACTIVE_CLASS1]) as p_name, \
         patch("handlers.identity.search_policies_by_cid",  return_value=[CD_POLICY_ACTIVE_CLASS1]), \
         patch("handlers.identity.search_policies_by_plate", return_value=CD_POLICY_ACTIVE_CLASS1), \
         patch("handlers.identity.search_policies_by_name",  return_value=[CD_POLICY_ACTIVE_CLASS1]):
        yield {
            "by_cid":   p_cid,
            "by_plate": p_plate,
            "by_name":  p_name,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers exposed to tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def set_session(main_module):
    """
    Factory fixture: allows tests to pre-seed user_sessions with a given state.

    Usage:
        set_session(user_id, {"state": "waiting_for_counterpart", "policy_info": ...})
    """
    def _set(user_id: str, session_data: Dict[str, Any]):
        main_module.user_sessions[user_id] = session_data

    return _set


@pytest.fixture()
def get_session(main_module):
    """Factory fixture: read user_sessions for inspection."""
    def _get(user_id: str) -> Dict:
        return main_module.user_sessions.get(user_id, {})

    return _get
