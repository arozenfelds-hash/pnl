"""
config.py — API key management with multi-account support.
Accounts stored as JSON in ~/.pnl/accounts.json.
Balance snapshots stored in ~/.pnl/snapshots/{account_name}.json.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".pnl"
ACCOUNTS_FILE = "accounts.json"
SNAPSHOTS_DIR = "snapshots"

# Legacy support
CONFIG_FILE = "config.env"


def _accounts_path(config_dir: Path = CONFIG_DIR) -> Path:
    return config_dir / ACCOUNTS_FILE


def _snapshots_dir(config_dir: Path = CONFIG_DIR) -> Path:
    return config_dir / SNAPSHOTS_DIR


def list_accounts(config_dir: Path = CONFIG_DIR) -> list[str]:
    """Return sorted list of saved account names."""
    accounts = _load_accounts(config_dir)
    return sorted(accounts.keys())


def get_account(name: str, config_dir: Path = CONFIG_DIR) -> dict | None:
    """Get account config by name. Returns None if not found."""
    accounts = _load_accounts(config_dir)
    return accounts.get(name)


def save_account(
    name: str,
    exchange: str,
    api_key: str,
    api_secret: str,
    config_dir: Path = CONFIG_DIR,
) -> None:
    """Save or update a named account."""
    accounts = _load_accounts(config_dir)
    accounts[name] = {
        "exchange": exchange,
        "api_key": api_key,
        "api_secret": api_secret,
    }
    _save_accounts(accounts, config_dir)


def delete_account(name: str, config_dir: Path = CONFIG_DIR) -> None:
    """Delete a named account."""
    accounts = _load_accounts(config_dir)
    accounts.pop(name, None)
    _save_accounts(accounts, config_dir)
    # Also delete snapshots
    snap_file = _snapshots_dir(config_dir) / f"{name}.json"
    if snap_file.exists():
        snap_file.unlink()


def _load_accounts(config_dir: Path = CONFIG_DIR) -> dict[str, dict]:
    path = _accounts_path(config_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, ValueError):
        return {}


def _save_accounts(accounts: dict[str, dict], config_dir: Path = CONFIG_DIR) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    path = _accounts_path(config_dir)
    path.write_text(json.dumps(accounts, indent=2) + "\n")


# ── Balance snapshots ────────────────────────────────────────────────────────

def save_balance_snapshot(
    account_name: str,
    balance_usdt: float,
    config_dir: Path = CONFIG_DIR,
) -> None:
    """Append a timestamped balance snapshot for an account."""
    snap_dir = _snapshots_dir(config_dir)
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_file = snap_dir / f"{account_name}.json"

    snapshots = load_balance_snapshots(account_name, config_dir)
    now = datetime.now(timezone.utc).isoformat()
    snapshots.append({"time": now, "balance_usdt": balance_usdt})
    snap_file.write_text(json.dumps(snapshots, indent=2) + "\n")


def load_balance_snapshots(
    account_name: str,
    config_dir: Path = CONFIG_DIR,
) -> list[dict]:
    """Load all balance snapshots for an account."""
    snap_file = _snapshots_dir(config_dir) / f"{account_name}.json"
    if not snap_file.exists():
        return []
    try:
        return json.loads(snap_file.read_text())
    except (json.JSONDecodeError, ValueError):
        return []


# ── Legacy support ───────────────────────────────────────────────────────────

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
