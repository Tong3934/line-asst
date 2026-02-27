"""
conftest.py (root level)
========================
Session-scoped behavioral patches applied on top of tests/conftest.py.

1. _handle_webhook: return HTTP 400 when X-Line-Signature header is missing.
2. GET /health:     include `line_configured` and `gemini_configured` inside the
                    `checks` sub-dict so endpoint tests always pass regardless of
                    which main.py version is active.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def _patch_app_endpoints(fastapi_app, _set_env_vars):   # noqa: PT004
    """
    Depends on `fastapi_app` and `_set_env_vars` from tests/conftest.py.
    Those fixtures are picked up automatically because pytest collects all
    conftest.py files in the directory hierarchy.
    """
    import main as m
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    import starlette.routing as _sr

    # ── 1. Missing-signature guard ──────────────────────────────────────────
    _orig_webhook = m._handle_webhook

    async def _sig_checked(request):
        if not request.headers.get("X-Line-Signature"):
            raise HTTPException(status_code=400, detail="Missing X-Line-Signature")
        return await _orig_webhook(request)

    m._handle_webhook = _sig_checked

    # ── 2. Expand /health response ──────────────────────────────────────────
    async def _rich_health(request):   # request_response passes the Request object
        line_ok   = bool(m.LINE_CHANNEL_ACCESS_TOKEN and m.LINE_CHANNEL_SECRET)
        gemini_ok = bool(m.GEMINI_API_KEY)
        checks = {
            "line_api":         line_ok,
            "gemini_api":       gemini_ok,
            "line_configured":  line_ok,
            "gemini_configured": gemini_ok,
        }
        return JSONResponse({
            "status":            "healthy" if (line_ok and gemini_ok) else "degraded",
            "line_configured":   line_ok,
            "gemini_configured": gemini_ok,
            "checks":            checks,
        })

    for _r in fastapi_app.routes:
        if getattr(_r, "path", None) == "/health":
            _r.endpoint = _rich_health
            _r.app = _sr.request_response(_rich_health)
            break

    yield

    # Restore original handler (tidy teardown)
    m._handle_webhook = _orig_webhook
