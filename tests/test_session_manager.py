"""
test_session_manager.py
=======================
Unit tests for session_manager.py — the stateful session layer.

Areas covered
-------------
  SM-01  get_session()      — creation of default sessions & retrieval
  SM-02  set_state()        — state mutation and kwargs storage
  SM-03  reset_session()    — full session wipe with default / custom state
  SM-04  Session isolation  — multiple users don't bleed into each other
  SM-05  process_search_result() — four execution paths:
           • empty policy list  → False + reply "not found"
           • single policy      → True + advance to waiting_for_counterpart
           • multiple policies  → True + advance to waiting_for_vehicle_selection
           • use_push=True      → push_message, not reply_message
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_data import (
    USER_ID_A,
    USER_ID_B,
    CD_POLICY_ACTIVE_CLASS1,
    CD_POLICY_ACTIVE_CLASS2PLUS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clear():
    """Reset user_sessions before each test that needs a clean slate."""
    from session_manager import user_sessions
    user_sessions.clear()


def _make_api_event():
    """Return a (line_bot_api_mock, event_mock) pair."""
    api = MagicMock()
    api.reply_message = MagicMock(return_value=None)
    api.push_message  = MagicMock(return_value=None)
    event = MagicMock()
    event.reply_token = "tok_test_001"
    return api, event


# ─────────────────────────────────────────────────────────────────────────────
# SM-01  get_session()
# ─────────────────────────────────────────────────────────────────────────────

class TestGetSession:
    """SM-01: get_session creates and retrieves sessions correctly."""

    def setup_method(self):
        _clear()

    def test_new_user_gets_idle_state(self):
        from session_manager import get_session
        session = get_session("brand_new_user")
        assert session["state"] == "idle"

    def test_new_user_session_is_stored_in_dict(self):
        from session_manager import user_sessions, get_session
        get_session("stored_user")
        assert "stored_user" in user_sessions

    def test_get_existing_user_returns_persisted_data(self):
        from session_manager import user_sessions, get_session
        user_sessions[USER_ID_A] = {"state": "waiting_for_info", "custom_key": "hello"}
        session = get_session(USER_ID_A)
        assert session["state"] == "waiting_for_info"
        assert session["custom_key"] == "hello"

    def test_get_existing_user_does_not_overwrite(self):
        from session_manager import user_sessions, get_session
        user_sessions[USER_ID_A] = {"state": "waiting_for_counterpart", "policy_info": {"plate": "กก1234"}}
        get_session(USER_ID_A)  # call again
        assert user_sessions[USER_ID_A]["state"] == "waiting_for_counterpart"
        assert "policy_info" in user_sessions[USER_ID_A]

    def test_returns_same_dict_object_as_stored(self):
        from session_manager import user_sessions, get_session
        session = get_session("ref_user")
        session["extra"] = "value"
        assert user_sessions["ref_user"]["extra"] == "value"

    def test_two_different_users_get_independent_sessions(self):
        from session_manager import get_session
        sa = get_session(USER_ID_A)
        sb = get_session(USER_ID_B)
        sa["state"] = "waiting_for_info"
        assert sb["state"] == "idle"


# ─────────────────────────────────────────────────────────────────────────────
# SM-02  set_state()
# ─────────────────────────────────────────────────────────────────────────────

class TestSetState:
    """SM-02: set_state writes state & keyword arguments into the session."""

    def setup_method(self):
        _clear()

    def test_state_field_is_updated(self):
        from session_manager import user_sessions, set_state
        set_state(USER_ID_A, "waiting_for_info")
        assert user_sessions[USER_ID_A]["state"] == "waiting_for_info"

    def test_kwargs_are_stored(self):
        from session_manager import user_sessions, set_state
        set_state(USER_ID_A, "waiting_for_counterpart", policy_info={"plate": "กก1234"})
        assert user_sessions[USER_ID_A]["policy_info"]["plate"] == "กก1234"

    def test_multiple_kwargs_all_stored(self):
        from session_manager import user_sessions, set_state
        set_state(
            USER_ID_A, "waiting_for_image",
            temp_image_bytes=b"\xff\xd8",
            has_counterpart="มีคู่กรณี",
            policy_info=CD_POLICY_ACTIVE_CLASS1,
        )
        assert user_sessions[USER_ID_A]["temp_image_bytes"] == b"\xff\xd8"
        assert user_sessions[USER_ID_A]["has_counterpart"] == "มีคู่กรณี"
        assert user_sessions[USER_ID_A]["policy_info"] is not None

    def test_creates_new_user_if_absent(self):
        from session_manager import user_sessions, set_state
        set_state("totally_new", "waiting_for_info")
        assert "totally_new" in user_sessions
        assert user_sessions["totally_new"]["state"] == "waiting_for_info"

    def test_overwrites_previous_state(self):
        from session_manager import user_sessions, set_state
        user_sessions[USER_ID_A] = {"state": "waiting_for_info"}
        set_state(USER_ID_A, "waiting_for_counterpart")
        assert user_sessions[USER_ID_A]["state"] == "waiting_for_counterpart"

    def test_existing_keys_preserved_if_not_in_kwargs(self):
        from session_manager import user_sessions, set_state
        user_sessions[USER_ID_A] = {"state": "idle", "legacy_key": "keep_me"}
        set_state(USER_ID_A, "waiting_for_info")
        assert user_sessions[USER_ID_A]["legacy_key"] == "keep_me"

    def test_kwarg_overwrites_existing_key(self):
        from session_manager import user_sessions, set_state
        user_sessions[USER_ID_A] = {"state": "idle", "has_counterpart": "มีคู่กรณี"}
        set_state(USER_ID_A, "waiting_for_image", has_counterpart="ไม่มีคู่กรณี")
        assert user_sessions[USER_ID_A]["has_counterpart"] == "ไม่มีคู่กรณี"


# ─────────────────────────────────────────────────────────────────────────────
# SM-03  reset_session()
# ─────────────────────────────────────────────────────────────────────────────

class TestResetSession:
    """SM-03: reset_session wipes data and sets initial state."""

    def setup_method(self):
        _clear()

    def test_defaults_to_idle(self):
        from session_manager import user_sessions, reset_session
        user_sessions[USER_ID_A] = {"state": "waiting_for_image", "junk": True}
        reset_session(USER_ID_A)
        assert user_sessions[USER_ID_A]["state"] == "idle"

    def test_custom_initial_state_applied(self):
        from session_manager import user_sessions, reset_session
        reset_session(USER_ID_A, initial_state="waiting_for_info")
        assert user_sessions[USER_ID_A]["state"] == "waiting_for_info"

    def test_all_extra_keys_cleared(self):
        from session_manager import user_sessions, reset_session
        user_sessions[USER_ID_A] = {
            "state":           "waiting_for_image",
            "policy_info":     CD_POLICY_ACTIVE_CLASS1,
            "temp_image_bytes": b"data",
            "has_counterpart": "มีคู่กรณี",
        }
        reset_session(USER_ID_A)
        assert len(user_sessions[USER_ID_A]) == 1
        assert list(user_sessions[USER_ID_A].keys()) == ["state"]

    def test_reset_new_user_creates_entry(self):
        from session_manager import user_sessions, reset_session
        reset_session("fresh_user")
        assert user_sessions["fresh_user"]["state"] == "idle"

    def test_reset_does_not_affect_other_users(self):
        from session_manager import user_sessions, reset_session, set_state
        set_state(USER_ID_A, "waiting_for_info", policy_info={})
        set_state(USER_ID_B, "waiting_for_counterpart")
        reset_session(USER_ID_A)
        assert user_sessions[USER_ID_B]["state"] == "waiting_for_counterpart"


# ─────────────────────────────────────────────────────────────────────────────
# SM-04  Session isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionIsolation:
    """SM-04: sessions for different users are fully independent."""

    def setup_method(self):
        _clear()

    def test_user_a_data_not_in_user_b(self):
        from session_manager import get_session, set_state
        set_state(USER_ID_A, "waiting_for_info", policy_info=CD_POLICY_ACTIVE_CLASS1)
        sb = get_session(USER_ID_B)
        assert sb.get("state") == "idle"
        assert "policy_info" not in sb

    def test_modifying_user_b_does_not_change_user_a(self):
        from session_manager import get_session, set_state
        set_state(USER_ID_A, "waiting_for_counterpart")
        set_state(USER_ID_B, "waiting_for_image")
        set_state(USER_ID_B, "completed")
        assert get_session(USER_ID_A)["state"] == "waiting_for_counterpart"

    def test_clearing_user_a_does_not_remove_user_b(self):
        from session_manager import user_sessions, get_session, reset_session
        get_session(USER_ID_A)
        get_session(USER_ID_B)
        reset_session(USER_ID_A)
        assert USER_ID_B in user_sessions

    def test_ten_concurrent_users_independent(self):
        from session_manager import set_state, get_session
        uids = [f"U{i:04d}" for i in range(10)]
        for i, uid in enumerate(uids):
            set_state(uid, f"state_{i}")
        for i, uid in enumerate(uids):
            assert get_session(uid)["state"] == f"state_{i}"


# ─────────────────────────────────────────────────────────────────────────────
# SM-05  process_search_result()
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessSearchResult:
    """SM-05: process_search_result branches correctly on policy count."""

    def setup_method(self):
        _clear()

    def test_empty_list_returns_false(self):
        from session_manager import process_search_result
        api, event = _make_api_event()
        result = process_search_result(api, event, USER_ID_A, [])
        assert result is False

    def test_empty_list_sends_not_found_message(self):
        from session_manager import process_search_result
        api, event = _make_api_event()
        process_search_result(api, event, USER_ID_A, [])
        api.reply_message.assert_called_once()

    def test_single_policy_returns_true(self):
        from session_manager import process_search_result
        api, event = _make_api_event()
        result = process_search_result(api, event, USER_ID_A, [CD_POLICY_ACTIVE_CLASS1])
        assert result is True

    def test_single_policy_advances_to_waiting_for_counterpart(self):
        from session_manager import user_sessions, process_search_result
        api, event = _make_api_event()
        process_search_result(api, event, USER_ID_A, [CD_POLICY_ACTIVE_CLASS1])
        assert user_sessions[USER_ID_A]["state"] == "waiting_for_counterpart"

    def test_single_policy_stores_policy_info(self):
        from session_manager import user_sessions, process_search_result
        api, event = _make_api_event()
        process_search_result(api, event, USER_ID_A, [CD_POLICY_ACTIVE_CLASS1])
        assert user_sessions[USER_ID_A].get("policy_info") is not None
        assert user_sessions[USER_ID_A]["policy_info"]["plate"] == "กก1234"

    def test_single_policy_sends_reply(self):
        from session_manager import process_search_result
        api, event = _make_api_event()
        process_search_result(api, event, USER_ID_A, [CD_POLICY_ACTIVE_CLASS1])
        api.reply_message.assert_called_once()

    def test_multiple_policies_returns_true(self):
        from session_manager import process_search_result
        api, event = _make_api_event()
        result = process_search_result(
            api, event, USER_ID_A, [CD_POLICY_ACTIVE_CLASS1, CD_POLICY_ACTIVE_CLASS2PLUS]
        )
        assert result is True

    def test_multiple_policies_advances_to_vehicle_selection(self):
        from session_manager import user_sessions, process_search_result
        api, event = _make_api_event()
        process_search_result(
            api, event, USER_ID_A, [CD_POLICY_ACTIVE_CLASS1, CD_POLICY_ACTIVE_CLASS2PLUS]
        )
        assert user_sessions[USER_ID_A]["state"] == "waiting_for_vehicle_selection"

    def test_multiple_policies_stored_in_search_results(self):
        from session_manager import user_sessions, process_search_result
        policies = [CD_POLICY_ACTIVE_CLASS1, CD_POLICY_ACTIVE_CLASS2PLUS]
        api, event = _make_api_event()
        process_search_result(api, event, USER_ID_A, policies)
        assert len(user_sessions[USER_ID_A]["search_results"]) == 2

    def test_use_push_calls_push_message_not_reply(self):
        from session_manager import process_search_result
        api, event = _make_api_event()
        process_search_result(api, event, USER_ID_A, [], use_push=True)
        api.push_message.assert_called_once()
        api.reply_message.assert_not_called()

    def test_use_push_single_policy_uses_push(self):
        from session_manager import process_search_result
        api, event = _make_api_event()
        process_search_result(api, event, USER_ID_A, [CD_POLICY_ACTIVE_CLASS1], use_push=True)
        api.push_message.assert_called_once()
        api.reply_message.assert_not_called()

    def test_use_push_multiple_policies_uses_push(self):
        from session_manager import process_search_result
        api, event = _make_api_event()
        process_search_result(
            api, event, USER_ID_A,
            [CD_POLICY_ACTIVE_CLASS1, CD_POLICY_ACTIVE_CLASS2PLUS],
            use_push=True,
        )
        api.push_message.assert_called_once()
        api.reply_message.assert_not_called()
