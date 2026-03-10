"""
config.py — API key management.
Load/save exchange API keys from ~/.pnl/config.env.
"""
from __future__ import annotations

from pathlib import Path

CONFIG_DIR = Path.home() / ".pnl"
CONFIG_FILE = "config.env"


def load_keys(config_dir: Path = CONFIG_DIR) -> dict[str, str]:
    """Load key=value pairs from config.env. Returns empty dict if missing."""
    env_path = config_dir / CONFIG_FILE
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def save_keys(keys: dict[str, str], config_dir: Path = CONFIG_DIR) -> None:
    """Save key=value pairs to config.env. Creates directory if needed."""
    config_dir.mkdir(parents=True, exist_ok=True)
    env_path = config_dir / CONFIG_FILE
    lines = [f"{k}={v}" for k, v in keys.items()]
    env_path.write_text("\n".join(lines) + "\n")
