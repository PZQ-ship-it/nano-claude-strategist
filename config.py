"""Configuration management for nano claude (multi-provider)."""
import os
import json
from pathlib import Path

CONFIG_DIR   = Path.home() / ".nano_claude"
CONFIG_FILE  = CONFIG_DIR  / "config.json"
HISTORY_FILE = CONFIG_DIR  / "input_history.txt"
SESSIONS_DIR = CONFIG_DIR  / "sessions"

MR_SESSION_DIR = SESSIONS_DIR / "mr_sessions"


def _load_dotenv_if_present() -> None:
    """Load .env from cwd into process env (without overriding existing vars)."""
    env_file = Path.cwd() / ".env"
    if not env_file.exists() or not env_file.is_file():
        return

    try:
        for raw_line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            if key in os.environ:
                continue  # keep explicit shell/runtime env values

            value = value.strip()
            if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
                value = value[1:-1]
            os.environ[key] = value
    except Exception:
        # Never fail app startup due to .env parsing quirks.
        return


def _sanitize_ssl_env() -> None:
    """Remove broken SSL env overrides that can crash httpx/OpenAI client init."""
    cert_file = os.environ.get("SSL_CERT_FILE", "").strip()
    if cert_file and not Path(cert_file).exists():
        os.environ.pop("SSL_CERT_FILE", None)

    cert_dir = os.environ.get("SSL_CERT_DIR", "").strip()
    if cert_dir and not Path(cert_dir).exists():
        os.environ.pop("SSL_CERT_DIR", None)

DEFAULTS = {
    "model":            "ollama/gemma4:e4b",
    "max_tokens":       40000,
    "permission_mode":  "auto",   # auto | accept-all | manual
    "verbose":          False,
    "thinking":         False,
    "thinking_budget":  10000,
    "custom_base_url":  "",       # for "custom" provider
    "max_tool_output":  32000,
    "max_agent_depth":  3,
    "max_concurrent_agents": 3,
    # Per-provider API keys (optional; env vars take priority)
    # "anthropic_api_key": "sk-ant-..."
    # "openai_api_key":    "sk-..."
    # "gemini_api_key":    "..."
    # "kimi_api_key":      "..."
    # "qwen_api_key":      "..."
    # "zhipu_api_key":     "..."
    # "deepseek_api_key":  "..."
}


def load_config() -> dict:
    _load_dotenv_if_present()
    _sanitize_ssl_env()
    CONFIG_DIR.mkdir(exist_ok=True)
    SESSIONS_DIR.mkdir(exist_ok=True)
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text()))
        except Exception:
            pass
    # Backward-compat: legacy single api_key → anthropic_api_key
    if cfg.get("api_key") and not cfg.get("anthropic_api_key"):
        cfg["anthropic_api_key"] = cfg.pop("api_key")
    # Also accept ANTHROPIC_API_KEY env for backward-compat
    if not cfg.get("anthropic_api_key"):
        cfg["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY", "")

    # Prefer custom endpoint from .env when model is still the built-in default.
    custom_base = os.environ.get("CUSTOM_BASE_URL", "").strip()
    custom_model = os.environ.get("CUSTOM_MODEL", "").strip()
    if custom_base and not cfg.get("custom_base_url"):
        cfg["custom_base_url"] = custom_base
    if custom_base and cfg.get("model") == DEFAULTS["model"]:
        cfg["model"] = f"custom/{custom_model or 'gpt-4o-mini'}"

    return cfg


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(exist_ok=True)
    # Strip internal runtime keys (e.g. _run_query_callback) before saving
    data = {k: v for k, v in cfg.items() if not k.startswith("_")}
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def current_provider(cfg: dict) -> str:
    from providers import detect_provider
    return detect_provider(cfg.get("model", "claude-opus-4-6"))


def has_api_key(cfg: dict) -> bool:
    """Check whether the active provider has an API key configured."""
    from providers import get_api_key
    pname = current_provider(cfg)
    key = get_api_key(pname, cfg)
    return bool(key)


def calc_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    from providers import calc_cost as _cc
    return _cc(model, in_tokens, out_tokens)
