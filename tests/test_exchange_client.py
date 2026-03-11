from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pandas as pd
import pytest

from exchange_client import (
    create_exchange,
    fetch_trades,
    normalize_trades,
    SUPPORTED_EXCHANGES,
)


def test_supported_exchanges():
    assert "binance" in SUPPORTED_EXCHANGES
    assert "bybit" in SUPPORTED_EXCHANGES


def test_create_exchange_invalid():
    with pytest.raises(ValueError, match="Unsupported exchange"):
        create_exchange("kraken", "key", "secret")


def test_normalize_trades_binance_format():
    """Binance trade format -> unified DataFrame."""
    raw_trades = [
        {
            "id": "1",
            "timestamp": 1700000000000,
            "datetime": "2023-11-14T22:13:20.000Z",
            "symbol": "BTC/USDT",
            "side": "buy",
            "price": 35000.0,
            "amount": 0.01,
            "cost": 350.0,
            "fee": {"cost": 0.07, "currency": "USDT"},
        },
        {
            "id": "2",
            "timestamp": 1700000060000,
            "datetime": "2023-11-14T22:14:20.000Z",
            "symbol": "BTC/USDT",
            "side": "sell",
            "price": 35100.0,
            "amount": 0.01,
            "cost": 351.0,
            "fee": {"cost": 0.07, "currency": "USDT"},
        },
    ]
    df = normalize_trades(raw_trades)
    assert len(df) == 2
    assert list(df.columns) == [
        "time", "symbol", "side", "price", "amount", "cost", "fee", "fee_currency",
        "reduce_only",
    ]
    assert df.iloc[0]["side"] == "buy"
    assert df.iloc[1]["price"] == 35100.0
    assert df.iloc[0]["fee"] == 0.07


def test_normalize_trades_empty():
    df = normalize_trades([])
    assert len(df) == 0
    assert "time" in df.columns
