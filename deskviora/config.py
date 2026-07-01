"""
Local settings storage for DeskViora.
Keeps the API key and a couple of preferences in a small JSON file next to
the executable (or in the user's home folder if that's not writable), so
the person only has to enter their key once.
"""

import json
import os
import sys

APP_NAME = "DeskViora"


def _config_dir() -> str:
    """Pick a writable place to store settings, next to the exe if possible."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    try:
        test_path = os.path.join(base, ".write_test")
        with open(test_path, "w") as f:
            f.write("ok")
        os.remove(test_path)
        return base
    except Exception:
        # Fall back to the user's home directory if the exe folder is
        # read-only (e.g. installed under Program Files).
        home = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")
        os.makedirs(home, exist_ok=True)
        return home


CONFIG_PATH = os.path.join(_config_dir(), "settings.json")

DEFAULTS = {
    "api_key": "",
    # Any vision-capable model on OpenRouter works. Swap this for a direct
    # Anthropic/OpenAI key + model if you'd rather not go through OpenRouter.
    "model": "anthropic/claude-sonnet-4.5",
    "api_base": "https://openrouter.ai/api/v1/chat/completions",
    "screenshot_scale": 1.0,   # downscale screenshots before sending, for cost/speed
    "confirm_before_typing_sensitive": True,
}


def load() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULTS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
