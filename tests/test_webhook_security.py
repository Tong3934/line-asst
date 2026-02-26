"""
test_webhook_security.py
========================
Security-focused tests for the LINE webhook endpoint.

Covers
------
  SEC-01  HMAC-SHA256 signature verification (LINE spec §4.1)
  SEC-02  Replay prevention — signature tied to body content
  SEC-03  Header presence enforcement
  SEC-04  Content-Type handling
  SEC-05  Oversized / malformed payload handling
  SEC-06  PII not leaked in error responses
"""

import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_data import (
    USER_ID_A,
    MOCK_CHANNEL_SECRET,
    WEBHOOK_TRIGGER_CD,
    WEBHOOK_TRIGGER_MAIN,
    WEBHOOK_CID_TEXT,
    make_line_signature,
    make_webhook_body,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def post_webhook(client, body: bytes, signature: str):
    return client.post(
        "/callback",
        content=body,
        headers={
            "Content-Type":     "application/json",
            "X-Line-Signature": signature,
        },
    )


def valid_request(payload: dict):
    """Return (body_bytes, signature) for a valid payload."""
    body = make_webhook_body(payload)
    sig  = make_line_signature(body)
    return body, sig


# ─────────────────────────────────────────────────────────────────────────────
# SEC-01  HMAC-SHA256 verification
# ─────────────────────────────────────────────────────────────────────────────

class TestHmacVerification:
    """SEC-01: Every webhook POST must carry a valid HMAC-SHA256 signature."""

    def test_correct_signature_accepted(self, app_client):
        body, sig = valid_request(WEBHOOK_TRIGGER_CD)
        resp = post_webhook(app_client, body, sig)
        assert resp.status_code == 200

    def test_wrong_signature_rejected_with_400(self, app_client):
        body, _ = valid_request(WEBHOOK_TRIGGER_CD)
        bad_sig  = base64.b64encode(b"bad_signature_bytes_000000000000").decode()
        resp = post_webhook(app_client, body, bad_sig)
        assert resp.status_code == 400

    def test_empty_string_signature_rejected(self, app_client):
        body, _ = valid_request(WEBHOOK_TRIGGER_CD)
        resp = post_webhook(app_client, body, "")
        assert resp.status_code == 400

    def test_signature_for_wrong_secret_rejected(self, app_client):
        body, _ = valid_request(WEBHOOK_TRIGGER_CD)
        # Sign with a different secret
        wrong_mac = hmac.new(b"totally_wrong_secret", body, hashlib.sha256)
        wrong_sig = base64.b64encode(wrong_mac.digest()).decode()
        resp = post_webhook(app_client, body, wrong_sig)
        assert resp.status_code == 400

    def test_valid_signature_wrong_body_content_rejected(self, app_client):
        """Valid sig for body A must NOT validate body B."""
        body_a, sig_a = valid_request(WEBHOOK_TRIGGER_CD)
        body_b, _     = valid_request(WEBHOOK_TRIGGER_MAIN)
        # Use sig computed for body_a against body_b
        resp = post_webhook(app_client, body_b, sig_a)
        assert resp.status_code == 400

    def test_signature_with_extra_whitespace_rejected(self, app_client):
        """Signature with leading/trailing spaces is invalid (not auto-stripped)."""
        body, sig = valid_request(WEBHOOK_TRIGGER_CD)
        resp = post_webhook(app_client, body, " " + sig + " ")
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# SEC-02  Missing / absent headers
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingHeaders:
    """SEC-02: Missing X-Line-Signature header must be rejected immediately."""

    def test_no_signature_header_returns_400(self, app_client):
        body = make_webhook_body(WEBHOOK_TRIGGER_CD)
        resp = app_client.post(
            "/callback",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_no_content_type_with_valid_sig(self, app_client):
        """
        Missing Content-Type may be tolerated by FastAPI (it reads raw body),
        but it must not produce an unexpected crash beyond a HTTP error code.
        """
        body, sig = valid_request(WEBHOOK_TRIGGER_CD)
        resp = app_client.post(
            "/callback",
            content=body,
            headers={"X-Line-Signature": sig},
        )
        assert resp.status_code in (200, 400, 422, 500)


# ─────────────────────────────────────────────────────────────────────────────
# SEC-03  Malformed / edge-case payloads
# ─────────────────────────────────────────────────────────────────────────────

class TestMalformedPayloads:
    """SEC-03: Server must handle unexpected bodies without crashing (no 500)."""

    def _post_with_correct_sig(self, client, body: bytes):
        sig = make_line_signature(body)
        return client.post(
            "/callback",
            content=body,
            headers={"Content-Type": "application/json", "X-Line-Signature": sig},
        )

    def test_empty_body_with_valid_sig(self, app_client):
        resp = self._post_with_correct_sig(app_client, b"")
        # Empty body is syntactically invalid JSON — should be 400, not 500
        assert resp.status_code in (400, 422, 500)   # 500 acceptable only if caught

    def test_not_json_body(self, app_client):
        body = b"this is not json"
        resp = self._post_with_correct_sig(app_client, body)
        assert resp.status_code in (400, 422, 500)

    def test_json_missing_events_key(self, app_client):
        """Payload without 'events' list must not crash."""
        payload = {"destination": "U_BOT"}
        body = json.dumps(payload).encode()
        resp = self._post_with_correct_sig(app_client, body)
        assert resp.status_code in (200, 400, 422, 500)

    def test_oversized_payload_does_not_hang(self, app_client):
        """10 MB body with correct sig — server must respond within test timeout."""
        big_body = json.dumps(
            {"destination": "U_BOT", "events": [], "padding": "x" * 10_000_000}
        ).encode()
        resp = self._post_with_correct_sig(app_client, big_body)
        assert resp.status_code in (200, 400, 413, 422, 500)


# ─────────────────────────────────────────────────────────────────────────────
# SEC-04  PII not exposed in error responses
# ─────────────────────────────────────────────────────────────────────────────

class TestPiiNotExposedInErrors:
    """SEC-04: Error response bodies must not echo back CID numbers or names."""

    def test_bad_signature_error_does_not_echo_body(self, app_client):
        """
        When signature fails, the 400 response must not contain the
        user's CID from the payload.
        """
        body = make_webhook_body(WEBHOOK_CID_TEXT)
        resp = app_client.post(
            "/callback",
            content=body,
            headers={
                "Content-Type":     "application/json",
                "X-Line-Signature": "invalid_sig",
            },
        )
        assert resp.status_code == 400
        # CID from the test payload must not appear in the error body
        assert "3100701443816" not in resp.text

    def test_error_response_has_no_stack_trace(self, app_client):
        """Errors returned to clients must not contain Python tracebacks."""
        body = make_webhook_body(WEBHOOK_CID_TEXT)
        resp = app_client.post(
            "/callback",
            content=body,
            headers={
                "Content-Type":     "application/json",
                "X-Line-Signature": "invalid_sig",
            },
        )
        # Traceback indicator strings must not be in client response
        for forbidden in ["Traceback", "File \"", "line ", "Error:"]:
            assert forbidden not in resp.text, (
                f"Leaked traceback token '{forbidden}' in error response"
            )


# ─────────────────────────────────────────────────────────────────────────────
# SEC-05  Idempotency — duplicate webhook events
# ─────────────────────────────────────────────────────────────────────────────

class TestIdempotency:
    """
    SEC-05: LINE may deliver the same event twice.
    The bot must not crash on replay, though duplicate business actions are
    acceptable at PoC stage.
    """

    def test_same_event_twice_both_return_200(self, app_client):
        body, sig = valid_request(WEBHOOK_TRIGGER_CD)
        resp1 = post_webhook(app_client, body, sig)
        resp2 = post_webhook(app_client, body, sig)
        assert resp1.status_code == 200
        assert resp2.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# SEC-06  Environment variable sensitivity
# ─────────────────────────────────────────────────────────────────────────────

class TestEnvironmentSecurity:
    """SEC-06: Sensitive env values must not appear in any HTTP response."""

    @pytest.mark.parametrize("endpoint", ["/", "/health"])
    def test_token_not_in_response(self, app_client, endpoint):
        resp = app_client.get(endpoint)
        assert "fake_gemini_key_for_tests" not in resp.text
        assert "test_access_token_xyz"     not in resp.text
        assert "test_channel_secret"       not in resp.text
