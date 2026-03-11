import os
import tempfile
from pathlib import Path

import pytest

from config import (
    load_keys, save_keys, CONFIG_DIR,
    list_accounts, get_account, save_account, delete_account,
    save_balance_snapshot, load_balance_snapshots,
)


def test_load_keys_returns_empty_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_keys(config_dir=Path(tmpdir))
        assert result == {}


def test_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        keys = {
            "binance_api_key": "abc123",
            "binance_api_secret": "secret456",
        }
        save_keys(keys, config_dir=Path(tmpdir))
        loaded = load_keys(config_dir=Path(tmpdir))
        assert loaded["binance_api_key"] == "abc123"
        assert loaded["binance_api_secret"] == "secret456"


def test_save_creates_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        nested = Path(tmpdir) / "sub" / "dir"
        save_keys({"key": "val"}, config_dir=nested)
        assert (nested / "config.env").exists()


def test_load_keys_ignores_comments_and_blanks():
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / "config.env"
        env_file.write_text("# comment\n\nMY_KEY=hello\n")
        result = load_keys(config_dir=Path(tmpdir))
        assert result["MY_KEY"] == "hello"


# ── Multi-account tests ─────────────────────────────────────────────────────

def test_save_and_list_accounts():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        save_account("main", "binance", "key1", "sec1", config_dir=d)
        save_account("alt", "bybit", "key2", "sec2", config_dir=d)
        names = list_accounts(config_dir=d)
        assert names == ["alt", "main"]  # sorted


def test_get_account():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        save_account("test", "binance", "k", "s", config_dir=d)
        acc = get_account("test", config_dir=d)
        assert acc["exchange"] == "binance"
        assert acc["api_key"] == "k"
        assert get_account("nonexistent", config_dir=d) is None


def test_delete_account():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        save_account("tmp", "binance", "k", "s", config_dir=d)
        assert "tmp" in list_accounts(config_dir=d)
        delete_account("tmp", config_dir=d)
        assert "tmp" not in list_accounts(config_dir=d)


def test_balance_snapshots():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        assert load_balance_snapshots("acc1", config_dir=d) == []
        save_balance_snapshot("acc1", 1000.0, config_dir=d)
        save_balance_snapshot("acc1", 1050.0, config_dir=d)
        snaps = load_balance_snapshots("acc1", config_dir=d)
        assert len(snaps) == 2
        assert snaps[0]["balance_usdt"] == 1000.0
        assert snaps[1]["balance_usdt"] == 1050.0
        assert "time" in snaps[0]
