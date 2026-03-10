"""
exchange_client.py — CCXT exchange wrapper.
Connects to Binance/Bybit, fetches trade history (spot + futures).
"""
from __future__ import annotations

from datetime import datetime, timezone

import ccxt
import pandas as pd

SUPPORTED_EXCHANGES = {
    "binance": {
        "spot": "binance",
        "futures": "binanceusdm",
    },
    "bybit": {
        "spot": "bybit",
        "futures": "bybit",
    },
}

TRADE_COLUMNS = [
    "time", "symbol", "side", "price", "amount", "cost", "fee", "fee_currency",
]


def create_exchange(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    market_type: str = "spot",
) -> ccxt.Exchange:
    """Create a CCXT exchange instance. Raises ValueError for unsupported exchanges."""
    if exchange_name not in SUPPORTED_EXCHANGES:
        raise ValueError(
            f"Unsupported exchange: {exchange_name}. "
            f"Supported: {list(SUPPORTED_EXCHANGES.keys())}"
        )
    exc_config = SUPPORTED_EXCHANGES[exchange_name]
    exc_id = exc_config[market_type] if market_type in exc_config else exc_config["spot"]

    exchange_class = getattr(ccxt, exc_id)
    exchange = exchange_class({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
    })

    # Bybit futures needs options
    if exchange_name == "bybit" and market_type == "futures":
        exchange.options["defaultType"] = "swap"

    return exchange


def normalize_trades(raw_trades: list[dict]) -> pd.DataFrame:
    """Convert CCXT trade dicts to a clean DataFrame."""
    if not raw_trades:
        return pd.DataFrame(columns=TRADE_COLUMNS)

    rows = []
    for t in raw_trades:
        fee_info = t.get("fee") or {}
        rows.append({
            "time": pd.to_datetime(t["timestamp"], unit="ms", utc=True),
            "symbol": t["symbol"],
            "side": t["side"],
            "price": float(t["price"]),
            "amount": float(t["amount"]),
            "cost": float(t["cost"]),
            "fee": float(fee_info.get("cost", 0.0)),
            "fee_currency": fee_info.get("currency", "USDT"),
        })
    return pd.DataFrame(rows, columns=TRADE_COLUMNS)


def fetch_trades(
    exchange: ccxt.Exchange,
    symbol: str | None = None,
    since_ms: int | None = None,
    limit: int = 1000,
) -> list[dict]:
    """
    Paginated trade fetch. If symbol is None, fetches for all traded symbols.
    Returns list of raw CCXT trade dicts.
    """
    all_trades: list[dict] = []

    if symbol:
        symbols = [symbol]
    else:
        exchange.load_markets()
        symbols = list(exchange.markets.keys())

    for sym in symbols:
        cursor = since_ms
        while True:
            try:
                trades = exchange.fetch_my_trades(sym, since=cursor, limit=limit)
            except ccxt.BadSymbol:
                break
            except ccxt.ExchangeError:
                break
            if not trades:
                break
            all_trades.extend(trades)
            if len(trades) < limit:
                break
            cursor = trades[-1]["timestamp"] + 1

    return all_trades


def fetch_all_trades(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    since_ms: int | None = None,
) -> pd.DataFrame:
    """
    Fetch all trades (spot + futures) from an exchange.
    Returns unified DataFrame with a 'market_type' column.
    """
    all_dfs: list[pd.DataFrame] = []

    for market_type in ["spot", "futures"]:
        try:
            exc = create_exchange(exchange_name, api_key, api_secret, market_type)
            raw = fetch_trades(exc, symbol=None, since_ms=since_ms)
            df = normalize_trades(raw)
            if not df.empty:
                df["market_type"] = market_type
                all_dfs.append(df)
        except Exception:
            continue

    if not all_dfs:
        return pd.DataFrame(columns=TRADE_COLUMNS + ["market_type"])

    result = pd.concat(all_dfs, ignore_index=True)
    result = result.sort_values("time").reset_index(drop=True)
    return result
