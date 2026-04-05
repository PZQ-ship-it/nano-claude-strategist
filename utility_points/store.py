"""Persistent store for Utility Points (UP) mapping rules."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

_lock = threading.Lock()

DEFAULT_RULES: dict[str, float] = {
    "hour_saved": 100.0,
    "joy_high": 800.0,
    "energy_drain_heavy": -500.0,
    "health_improvement": 600.0,
    "stress_reduction": 300.0,
}


def _ups_file() -> Path:
    return Path.cwd() / ".nano_claude" / "utility_points.json"


def _default_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "rules": {},
        "aliases": {},
        "notes": "",
    }


def _load_user_payload() -> dict[str, Any]:
    fp = _ups_file()
    if not fp.exists():
        return _default_payload()
    try:
        data = json.loads(fp.read_text())
    except Exception:
        return _default_payload()

    if not isinstance(data, dict):
        return _default_payload()

    payload = _default_payload()
    payload.update({k: v for k, v in data.items() if k in payload})

    if not isinstance(payload.get("rules"), dict):
        payload["rules"] = {}
    if not isinstance(payload.get("aliases"), dict):
        payload["aliases"] = {}
    if not isinstance(payload.get("notes"), str):
        payload["notes"] = ""
    return payload


def _save_user_payload(payload: dict[str, Any]) -> None:
    fp = _ups_file()
    fp.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = datetime.now().isoformat()
    fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def _normalize_key(key: str) -> str:
    return "_".join(str(key).strip().lower().split())


def get_effective_rules() -> dict[str, float]:
    with _lock:
        payload = _load_user_payload()
        rules = {**DEFAULT_RULES}
        for key, value in payload.get("rules", {}).items():
            try:
                rules[_normalize_key(key)] = float(value)
            except (TypeError, ValueError):
                continue
        return rules


def list_rules_with_source() -> list[tuple[str, float, str]]:
    with _lock:
        payload = _load_user_payload()
        user_rules: dict[str, float] = {}
        for key, value in payload.get("rules", {}).items():
            try:
                user_rules[_normalize_key(key)] = float(value)
            except (TypeError, ValueError):
                continue

        merged = {**DEFAULT_RULES, **user_rules}
        rows: list[tuple[str, float, str]] = []
        for key in sorted(merged.keys()):
            source = "user" if key in user_rules else "default"
            rows.append((key, float(merged[key]), source))
        return rows


def set_rule(key: str, value: float) -> tuple[str, float, bool]:
    with _lock:
        norm_key = _normalize_key(key)
        payload = _load_user_payload()
        user_rules = payload.setdefault("rules", {})
        before = user_rules.get(norm_key)
        if before is None:
            before = DEFAULT_RULES.get(norm_key)
        user_rules[norm_key] = float(value)
        _save_user_payload(payload)
        return norm_key, float(value), before is None


def delete_rule(key: str) -> tuple[bool, bool]:
    """Delete a user override rule.

    Returns:
        (removed_override, still_exists_as_default)
    """
    with _lock:
        norm_key = _normalize_key(key)
        payload = _load_user_payload()
        payload_rules = payload.setdefault("rules", {})
        removed = norm_key in payload_rules
        if removed:
            payload_rules.pop(norm_key, None)
            _save_user_payload(payload)
        return removed, norm_key in DEFAULT_RULES


def reset_rules() -> None:
    with _lock:
        payload = _default_payload()
        _save_user_payload(payload)
