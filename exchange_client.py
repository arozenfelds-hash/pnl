"""
exchange_client.py — CCXT exchange wrapper.
Connects to Binance/Bybit, fetches trade history (spot + futures).
Features: symbol filtering, concurrent fetching, local parquet cache.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

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
    "reduce_only",
]

CACHE_DIR = Path.home() / ".pnl" / "cache"
MAX_WORKERS = 10


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
        info = t.get("info", {})
        # Detect reduce_only from CCXT or raw exchange data
        # Binance futures: realizedPnl != 0 means closing trade
        realized_pnl = info.get("realizedPnl") or info.get("realizedProfit") or "0"
        try:
            has_realized_pnl = float(realized_pnl) != 0
        except (ValueError, TypeError):
            has_realized_pnl = False
        reduce_only = (
            t.get("reduceOnly")
            or info.get("reduceOnly")
            or info.get("reduce_only")
            or info.get("isReduceOnly")
            or (info.get("closedSize") and float(info.get("closedSize", 0)) > 0)
            or has_realized_pnl
            or False
        )
        rows.append({
            "time": pd.to_datetime(t["timestamp"], unit="ms", utc=True),
            "symbol": t["symbol"],
            "side": t["side"],
            "price": float(t["price"]),
            "amount": float(t["amount"]),
            "cost": float(t["cost"]),
            "fee": float(fee_info.get("cost", 0.0)),
            "fee_currency": fee_info.get("currency", "USDT"),
            "reduce_only": bool(reduce_only),
        })
    return pd.DataFrame(rows, columns=TRADE_COLUMNS)


# ── Symbol filtering ────────────────────────────────────────────────────────

def _get_traded_symbols(exchange: ccxt.Exchange) -> list[str]:
    """
    Get only symbols the account has actually traded.
    Uses balance + open orders + positions to find active symbols,
    then falls back to all markets if those methods fail.
    """
    symbols: set[str] = set()
    exchange.load_markets()

    # Method 1: Non-zero balances → derive likely traded pairs
    try:
        bal = exchange.fetch_balance()
        for asset, amt in bal.get("total", {}).items():
            if float(amt or 0) > 0 and asset not in ("USDT", "USD", "USDC", "BUSD"):
                pair = f"{asset}/USDT"
                if pair in exchange.markets:
                    symbols.add(pair)
                # Also check futures format
                pair_fut = f"{asset}/USDT:USDT"
                if pair_fut in exchange.markets:
                    symbols.add(pair_fut)
    except Exception:
        pass

    # Method 2: Open orders
    try:
        if exchange.has.get("fetchOpenOrders"):
            orders = exchange.fetch_open_orders()
            for o in orders:
                if o.get("symbol"):
                    symbols.add(o["symbol"])
    except Exception:
        pass

    # Method 3: Open positions (futures)
    try:
        if exchange.has.get("fetchPositions"):
            positions = exchange.fetch_positions()
            for p in positions:
                if p.get("symbol") and float(p.get("contracts", 0) or 0) != 0:
                    symbols.add(p["symbol"])
    except Exception:
        pass

    # If we found some symbols, also load cached symbols from previous runs
    cached = _load_cached_symbols(exchange)
    symbols.update(cached)

    if symbols:
        return sorted(symbols)

    # Fallback: all markets (slow path)
    return sorted(exchange.markets.keys())


def _cache_symbols_path(exchange: ccxt.Exchange) -> Path:
    """Path to the cached symbols file for an exchange."""
    exc_id = exchange.id
    return CACHE_DIR / f"{exc_id}_symbols.json"


def _load_cached_symbols(exchange: ccxt.Exchange) -> set[str]:
    """Load previously discovered traded symbols from cache."""
    path = _cache_symbols_path(exchange)
    if path.exists():
        try:
            return set(json.loads(path.read_text()))
        except Exception:
            pass
    return set()


def _save_cached_symbols(exchange: ccxt.Exchange, symbols: set[str]):
    """Save discovered traded symbols to cache for future runs."""
    path = _cache_symbols_path(exchange)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    existing = _load_cached_symbols(exchange)
    merged = sorted(existing | symbols)
    path.write_text(json.dumps(merged))


# ── Trade fetching ──────────────────────────────────────────────────────────

def _fetch_trades_for_symbol(
    exchange: ccxt.Exchange,
    symbol: str,
    since_ms: int | None = None,
    limit: int = 1000,
) -> list[dict]:
    """Fetch all paginated trades for a single symbol."""
    trades_out: list[dict] = []
    cursor = since_ms
    while True:
        try:
            trades = exchange.fetch_my_trades(symbol, since=cursor, limit=limit)
        except (ccxt.BadSymbol, ccxt.ExchangeError):
            break
        if not trades:
            break
        trades_out.extend(trades)
        if len(trades) < limit:
            break
        cursor = trades[-1]["timestamp"] + 1
    return trades_out


def fetch_trades(
    exchange: ccxt.Exchange,
    symbol: str | None = None,
    since_ms: int | None = None,
    limit: int = 1000,
) -> list[dict]:
    """
    Paginated trade fetch with concurrency and symbol filtering.
    If symbol is None, fetches for traded symbols only (not all markets).
    """
    if symbol:
        return _fetch_trades_for_symbol(exchange, symbol, since_ms, limit)

    # Get filtered symbol list
    symbols = _get_traded_symbols(exchange)

    # Concurrent fetch across symbols
    all_trades: list[dict] = []
    discovered_symbols: set[str] = set()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_fetch_trades_for_symbol, exchange, sym, since_ms, limit): sym
            for sym in symbols
        }
        for future in as_completed(futures):
            sym = futures[future]
            try:
                trades = future.result()
                if trades:
                    all_trades.extend(trades)
                    discovered_symbols.add(sym)
            except Exception:
                pass

    # Save discovered symbols for next time
    if discovered_symbols:
        _save_cached_symbols(exchange, discovered_symbols)

    return all_trades


# ── Local trade cache ───────────────────────────────────────────────────────

def _cache_path(account_name: str, exchange_name: str, market_type: str) -> Path:
    """Path to the parquet cache file for an account+market."""
    safe_name = account_name.replace(" ", "_").replace("/", "_")
    return CACHE_DIR / f"{safe_name}_{exchange_name}_{market_type}.parquet"


def _load_cache(account_name: str, exchange_name: str, market_type: str) -> pd.DataFrame | None:
    """Load cached trades from parquet. Returns None if no cache."""
    path = _cache_path(account_name, exchange_name, market_type)
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def _save_cache(df: pd.DataFrame, account_name: str, exchange_name: str, market_type: str):
    """Save trades to parquet cache."""
    if df.empty:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(account_name, exchange_name, market_type)
    df.to_parquet(path, index=False)


def _extract_bybit_usd_total(bal: dict) -> float | None:
    """
    Extract Bybit's reported USD total from the raw API response.
    Bybit returns totalEquity/totalWalletBalance in result.list[0],
    or per-coin usdValue for funding accounts.
    """
    raw_info = bal.get("info", {})
    acct_list = raw_info.get("result", {}).get("list", [])
    if not acct_list:
        return None

    acct_data = acct_list[0]

    # Unified Trading: has totalEquity or totalWalletBalance
    equity = acct_data.get("totalEquity") or acct_data.get("totalWalletBalance")
    if equity:
        try:
            return float(equity)
        except (ValueError, TypeError):
            pass

    # Funding account: sum individual coin usdValue fields
    coins = acct_data.get("coin", [])
    if coins:
        usd_sum = 0.0
        for coin in coins:
            usd_val = coin.get("usdValue")
            if usd_val:
                try:
                    usd_sum += float(usd_val)
                except (ValueError, TypeError):
                    pass
        if usd_sum > 0:
            return usd_sum

    return None


def fetch_balance(
    exchange_name: str,
    api_key: str,
    api_secret: str,
) -> dict:
    """
    Fetch current account balance from an exchange.
    Returns dict with 'total_usdt' (combined), 'spot_usdt', 'futures_usdt',
    and 'balances' (per-asset breakdown).
    Uses exchange-reported USD totals when available (matches what user sees).
    """
    total_usdt = 0.0
    spot_usdt = 0.0
    futures_usdt = 0.0
    balances: dict[str, dict] = {}

    # Bybit: funding + unified; Binance: spot + futures
    if exchange_name == "bybit":
        account_types = [
            ("spot", {"type": "funding"}),       # Funding account
            ("spot", {"type": "unified"}),        # Unified Trading account
        ]
    else:
        account_types = [
            ("spot", {}),
            ("futures", {}),
        ]

    for i, (market_type, bal_params) in enumerate(account_types):
        market_total = 0.0
        try:
            exc = create_exchange(exchange_name, api_key, api_secret, market_type)
            bal = exc.fetch_balance(bal_params) if bal_params else exc.fetch_balance()

            # Use exchange-reported USD total if available (matches user's UI)
            reported = _extract_bybit_usd_total(bal) if exchange_name == "bybit" else None

            if reported is not None:
                market_total = reported
            else:
                # Fallback: manual conversion via ticker prices
                for asset, amt_val in bal.get("total", {}).items():
                    amt = float(amt_val) if amt_val else 0.0
                    if amt <= 0:
                        continue
                    if asset in ("USDT", "USD"):
                        market_total += amt
                    else:
                        try:
                            ticker = exc.fetch_ticker(f"{asset}/USDT")
                            price = float(ticker.get("last", 0) or 0)
                            market_total += amt * price
                        except Exception:
                            pass

            # Record per-asset breakdown
            label = "funding" if i == 0 else "trading"
            for asset, amt_val in bal.get("total", {}).items():
                amt = float(amt_val) if amt_val else 0.0
                if amt <= 0:
                    continue
                if asset not in balances:
                    balances[asset] = {"amount": 0.0, "market_type": label}
                balances[asset]["amount"] += amt

        except Exception:
            continue

        if i == 0:
            spot_usdt = market_total
        else:
            futures_usdt = market_total
        total_usdt += market_total

    # Exchange-specific account labels
    if exchange_name == "bybit":
        label_a, label_b = "Funding", "Unified Trading"
    else:
        label_a, label_b = "Spot", "Futures"

    return {
        "total_usdt": total_usdt,
        "spot_usdt": spot_usdt,
        "futures_usdt": futures_usdt,
        "account_a_label": label_a,
        "account_b_label": label_b,
        "balances": balances,
    }


def fetch_positions(
    exchange_name: str,
    api_key: str,
    api_secret: str,
) -> pd.DataFrame:
    """
    Fetch all open positions (futures).
    Returns DataFrame with: symbol, side, size, entry_price, mark_price,
    unrealized_pnl, leverage, margin_mode, notional.
    """
    rows: list[dict] = []
    try:
        exc = create_exchange(exchange_name, api_key, api_secret, "futures")
        exc.load_markets()
        positions = exc.fetch_positions()
        for p in positions:
            contracts = float(p.get("contracts", 0) or 0)
            if contracts == 0:
                continue
            entry = float(p.get("entryPrice", 0) or 0)
            mark = float(p.get("markPrice", 0) or 0)
            notional = float(p.get("notional", 0) or 0)
            upnl = float(p.get("unrealizedPnl", 0) or 0)
            rows.append({
                "symbol": p.get("symbol", ""),
                "side": p.get("side", ""),
                "size": contracts,
                "entry_price": entry,
                "mark_price": mark,
                "notional": abs(notional),
                "unrealized_pnl": upnl,
                "leverage": str(p.get("leverage", "")),
                "margin_mode": p.get("marginMode", ""),
            })
    except Exception:
        pass

    cols = ["symbol", "side", "size", "entry_price", "mark_price",
            "notional", "unrealized_pnl", "leverage", "margin_mode"]
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def fetch_deposits_withdrawals(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    since_ms: int | None = None,
) -> pd.DataFrame:
    """
    Fetch deposit and withdrawal history.
    Returns DataFrame with: time, type, currency, amount, amount_usdt, status.
    """
    rows: list[dict] = []
    exc = create_exchange(exchange_name, api_key, api_secret, "spot")

    # Deposits
    try:
        if exc.has.get("fetchDeposits"):
            deposits = exc.fetch_deposits(since=since_ms)
            for d in deposits:
                amt = float(d.get("amount", 0) or 0)
                rows.append({
                    "time": pd.to_datetime(d["timestamp"], unit="ms", utc=True),
                    "type": "deposit",
                    "currency": d.get("currency", ""),
                    "amount": amt,
                    "status": d.get("status", ""),
                })
    except Exception:
        pass

    # Withdrawals
    try:
        if exc.has.get("fetchWithdrawals"):
            withdrawals = exc.fetch_withdrawals(since=since_ms)
            for w in withdrawals:
                amt = float(w.get("amount", 0) or 0)
                rows.append({
                    "time": pd.to_datetime(w["timestamp"], unit="ms", utc=True),
                    "type": "withdrawal",
                    "currency": w.get("currency", ""),
                    "amount": amt,
                    "status": w.get("status", ""),
                })
    except Exception:
        pass

    cols = ["time", "type", "currency", "amount", "status"]
    if not rows:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(rows, columns=cols)
    return df.sort_values("time").reset_index(drop=True)


def fetch_all_trades(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    since_ms: int | None = None,
    account_name: str | None = None,
    market_filter: str = "all",
) -> pd.DataFrame:
    """
    Fetch all trades (spot + futures) from an exchange.
    Uses local parquet cache when account_name is provided —
    only fetches new trades since last cached timestamp.
    Returns unified DataFrame with a 'market_type' column.

    market_filter: "all" | "spot" | "futures" — controls which markets to fetch.
    Bybit: single unified account — fetch once, classify by symbol format.
    Binance: separate spot + futures accounts — fetch each independently.
    """
    all_dfs: list[pd.DataFrame] = []

    # Bybit unified: fetch once, then classify spot vs futures by symbol
    if exchange_name == "bybit":
        market_types = ["futures"]  # unified account, fetch once via swap
    else:
        # Binance: only fetch the requested market type(s)
        if market_filter == "spot":
            market_types = ["spot"]
        elif market_filter == "futures":
            market_types = ["futures"]
        else:
            market_types = ["spot", "futures"]

    for market_type in market_types:
        try:
            # Check cache first
            cached_df = None
            fetch_since = since_ms
            if account_name:
                cached_df = _load_cache(account_name, exchange_name, market_type)
                if cached_df is not None:
                    # Only fetch trades newer than cache
                    last_ts = int(cached_df["time"].max().timestamp() * 1000) + 1
                    if since_ms is None or last_ts > since_ms:
                        fetch_since = last_ts

            exc = create_exchange(exchange_name, api_key, api_secret, market_type)
            raw = fetch_trades(exc, symbol=None, since_ms=fetch_since)
            new_df = normalize_trades(raw)

            # Classify market type per trade by symbol format
            # Symbols with ":" (e.g. BTC/USDT:USDT, BTC/USDC:USDC) are futures/perps
            if not new_df.empty:
                new_df["market_type"] = new_df["symbol"].apply(
                    lambda s: "futures" if ":" in s else "spot"
                )

            if cached_df is not None and not new_df.empty:
                combined = pd.concat([cached_df, new_df], ignore_index=True)
                combined = combined.drop_duplicates(
                    subset=["time", "symbol", "side", "price", "amount"],
                    keep="last",
                )
                combined = combined.sort_values("time").reset_index(drop=True)
                if account_name:
                    _save_cache(combined, account_name, exchange_name, market_type)
                all_dfs.append(combined)
            elif cached_df is not None and new_df.empty:
                all_dfs.append(cached_df)
            elif not new_df.empty:
                if "market_type" not in new_df.columns:
                    new_df["market_type"] = market_type
                if account_name:
                    _save_cache(new_df, account_name, exchange_name, market_type)
                all_dfs.append(new_df)

        except Exception:
            continue

    if not all_dfs:
        return pd.DataFrame(columns=TRADE_COLUMNS + ["market_type"])

    result = pd.concat(all_dfs, ignore_index=True)

    # Filter by original since_ms if we loaded from cache
    if since_ms is not None:
        since_ts = pd.Timestamp(since_ms, unit="ms", tz="UTC")
        result = result[result["time"] >= since_ts]

    result = result.sort_values("time").reset_index(drop=True)
    return result
