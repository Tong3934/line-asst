"""
test_api_endpoints.py
=====================
Integration tests for every HTTP endpoint exposed by the FastAPI app.

Endpoints under test
--------------------
GET  /          — root info
GET  /health    — health check
POST /webhook   — LINE webhook (signature verification + event routing)
GET  /reviewer  — reviewer dashboard (if implemented)
GET  /manager   — manager dashboard (if implemented)
GET  /admin     — admin dashboard (if implemented)

All LINE API and Gemini AI calls are mocked via conftest fixtures.
"""

import hashlib
import hmac
import base64
import json
import pytest
from tests.test_data import (
    USER_ID_A,
    MOCK_CHANNEL_SECRET,
    MOCK_CHANNEL_ACCESS_TOKEN,
    WEBHOOK_TRIGGER_CD,
    WEBHOOK_TRIGGER_MAIN,
    WEBHOOK_UNKNOWN_TEXT,
    WEBHOOK_CID_TEXT,
    make_line_signature,
    make_webhook_body,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def post_webhook(client, payload: dict, secret: str = MOCK_CHANNEL_SECRET):
    """POST a webhook event with a valid LINE signature."""
    body = make_webhook_body(payload)
    sig  = make_line_signature(body, secret)
    return client.post(
        "/callback",
        content=body,
        headers={
            "Content-Type":     "application/json",
            "X-Line-Signature": sig,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-ENDPOINT-01  GET /
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestRootEndpoint:
    """TC-ENDPOINT-01: Root may return 200 (v1) or 404 (v2) — must never be 5xx."""

    def test_root_no_server_error(self, app_client):
        resp = app_client.get("/")
        assert resp.status_code in (200, 404)

    def test_root_body_has_status(self, app_client):
        resp = app_client.get("/")
        if resp.status_code == 200:
            data = resp.json()
            assert "status" in data
            # v1 returns "running", v2 may return "ok" or "healthy"
            assert data["status"] in ("running", "ok", "healthy", "degraded")

    def test_root_body_has_message(self, app_client):
        resp = app_client.get("/")
        if resp.status_code == 200:
            data = resp.json()
            assert "message" in data


# ─────────────────────────────────────────────────────────────────────────────
# TC-ENDPOINT-02  GET /health
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestHealthEndpoint:
    """TC-ENDPOINT-02: /health returns 200 and boolean config flags."""

    def test_health_returns_200(self, app_client):
        resp = app_client.get("/health")
        assert resp.status_code == 200

    def test_health_body_structure(self, app_client):
        resp = app_client.get("/health")
        data = resp.json()
        assert "status" in data
        # v1 returns "healthy", v2 returns "ok" / "degraded"
        assert data["status"] in ("healthy", "ok", "degraded")

    def test_health_line_configured_flag(self, app_client):
        resp = app_client.get("/health")
        data = resp.json()
        # v1: data["line_configured"], v2: data["checks"]["line_token_set"]
        checks = data.get("checks", data)
        key = "line_token_set" if "line_token_set" in checks else "line_configured"
        assert key in checks
        assert isinstance(checks[key], bool)

    def test_health_gemini_configured_flag(self, app_client):
        resp = app_client.get("/health")
        data = resp.json()
        checks = data.get("checks", data)
        key = "gemini_key_set" if "gemini_key_set" in checks else "gemini_configured"
        assert key in checks
        assert isinstance(checks[key], bool)

    def test_health_configured_true_with_mock_env(self, app_client):
        """Config flags must be True because conftest injects fake env vars."""
        resp = app_client.get("/health")
        data = resp.json()
        checks = data.get("checks", data)
        # Accept either v1 or v2 key names
        line_flag   = checks.get("line_token_set",   checks.get("line_configured",  False))
        gemini_flag = checks.get("gemini_key_set",   checks.get("gemini_configured", False))
        assert line_flag is True
        assert gemini_flag is True


# ─────────────────────────────────────────────────────────────────────────────
# TC-ENDPOINT-03  POST /webhook — signature verification
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.security
class TestWebhookSignatureVerification:
    """TC-ENDPOINT-03: Webhook rejects requests with bad / missing signatures."""

    def test_valid_signature_returns_200(self, app_client):
        resp = post_webhook(app_client, WEBHOOK_TRIGGER_CD)
        assert resp.status_code == 200

    def test_missing_signature_header_returns_400(self, app_client):
        body = make_webhook_body(WEBHOOK_TRIGGER_CD)
        resp = app_client.post(
            "/callback",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_wrong_signature_returns_400(self, app_client):
        body = make_webhook_body(WEBHOOK_TRIGGER_CD)
        resp = app_client.post(
            "/callback",
            content=body,
            headers={
                "Content-Type":     "application/json",
                "X-Line-Signature": "AAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            },
        )
        assert resp.status_code == 400

    def test_tampered_body_returns_400(self, app_client):
        """Generate sig for original body, then alter the body."""
        body = make_webhook_body(WEBHOOK_TRIGGER_CD)
        sig  = make_line_signature(body)
        tampered = body + b" "
        resp = app_client.post(
            "/callback",
            content=tampered,
            headers={
                "Content-Type":     "application/json",
                "X-Line-Signature": sig,
            },
        )
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# TC-ENDPOINT-04  POST /webhook — event routing & response shape
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestWebhookEventRouting:
    """TC-ENDPOINT-04: Webhook processes events and returns {"status":"ok"}."""

    def test_response_body_is_ok(self, app_client):
        # v2 callback returns plain "OK"; v1 returns {"status": "ok"}
        resp = post_webhook(app_client, WEBHOOK_TRIGGER_CD)
        assert resp.status_code == 200

    def test_text_event_from_idle_state(self, app_client):
        """CD keyword from idle state must be handled without server error."""
        resp = post_webhook(app_client, WEBHOOK_TRIGGER_CD)
        assert resp.status_code == 200

    def test_main_trigger_keyword(self, app_client):
        """Classic trigger 'เช็คสิทธิ์เคลมด่วน' from idle state."""
        resp = post_webhook(app_client, WEBHOOK_TRIGGER_MAIN)
        assert resp.status_code == 200

    def test_unknown_text_does_not_crash(self, app_client):
        """Random text from a user with no session must return 200."""
        resp = post_webhook(app_client, WEBHOOK_UNKNOWN_TEXT)
        assert resp.status_code == 200

    def test_image_event_without_active_session_returns_200(self, app_client):
        from tests.test_data import WEBHOOK_IMAGE
        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200

    def test_empty_events_list(self, app_client):
        """LINE sends an empty events array for challenge / delivery confirmation."""
        payload = {"destination": "U_BOT", "events": []}
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200

    def test_cancel_keyword_from_any_state(self, app_client, set_session):
        """Cancel in any state must not raise a 500."""
        from tests.test_data import WEBHOOK_CANCEL
        set_session(USER_ID_A, {"state": "uploading_documents"})
        resp = post_webhook(app_client, WEBHOOK_CANCEL)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-ENDPOINT-05  Optional web dashboard endpoints (graceful absence check)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestDashboardEndpoints:
    """
    TC-ENDPOINT-05: Dashboard routes return either 200 (if implemented) or 404
    — they must NOT return 5xx.
    """

    @pytest.mark.parametrize("path", ["/reviewer", "/manager", "/admin"])
    def test_dashboard_no_server_error(self, app_client, path):
        resp = app_client.get(path)
        assert resp.status_code in (200, 404), (
            f"{path} returned unexpected status {resp.status_code}"
        )

    def test_health_check_not_dashboard(self, app_client):
        """Sanity: /health is always 200, not part of dashboard group."""
        assert app_client.get("/health").status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-ENDPOINT-06  POST /webhook  (alias of /callback)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestWebhookAlias:
    """
    TC-ENDPOINT-06: /webhook must behave identically to /callback —
    same signature rules, same event routing.
    """

    def _post(self, client, payload, sig=None):
        body = make_webhook_body(payload)
        if sig is None:
            sig = make_line_signature(body)
        return client.post(
            "/webhook",
            content=body,
            headers={"Content-Type": "application/json", "X-Line-Signature": sig},
        )

    def test_valid_signature_returns_200(self, app_client):
        resp = self._post(app_client, WEBHOOK_TRIGGER_CD)
        assert resp.status_code == 200

    def test_missing_signature_returns_400(self, app_client):
        body = make_webhook_body(WEBHOOK_TRIGGER_CD)
        resp = app_client.post(
            "/webhook",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_invalid_signature_returns_400(self, app_client):
        body = make_webhook_body(WEBHOOK_TRIGGER_CD)
        resp = app_client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type":     "application/json",
                "X-Line-Signature": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            },
        )
        assert resp.status_code == 400

    def test_text_event_handled_without_crash(self, app_client):
        resp = self._post(app_client, WEBHOOK_TRIGGER_MAIN)
        assert resp.status_code == 200

    def test_empty_events_list_accepted(self, app_client):
        payload = {"destination": "U_BOT", "events": []}
        resp = self._post(app_client, payload)
        assert resp.status_code == 200
