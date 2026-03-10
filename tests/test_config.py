import os
import tempfile
from pathlib import Path

import pytest

from config import load_keys, save_keys, CONFIG_DIR


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
