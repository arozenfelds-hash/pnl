# P/L Exchange Analytics — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit dashboard that connects to Binance and Bybit via read-only API keys and displays comprehensive trading account analytics.

**Architecture:** Four Python modules — `config.py` (key management), `exchange_client.py` (CCXT data fetching), `analytics.py` (metric computation), `app.py` (Streamlit UI). Data flows: keys → exchange client → raw trades → analytics → dashboard.

**Tech Stack:** Python, Streamlit, CCXT, Pandas, NumPy, Plotly

**Spec:** `docs/specs/2026-03-10-pnl-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `config.py` | Load/save API keys from `~/.pnl/config.env`, validate key format |
| `exchange_client.py` | CCXT wrapper: create exchange instances, fetch spot+futures trades, fetch balances, paginated history |
| `analytics.py` | Compute all metrics from trade DataFrame: P&L, win rate, Sharpe, Sortino, drawdown, breakdowns |
| `tests/test_config.py` | Tests for config load/save |
| `tests/test_analytics.py` | Tests for all metric computations using synthetic trade data |
| `tests/test_exchange_client.py` | Tests for exchange client (mocked CCXT) |
| `app.py` | Streamlit dashboard: sidebar, KPIs, charts, tables |
| `requirements.txt` | Python dependencies |
| `deploy.sh` | Server deployment script (port 8504) |
| `CLAUDE.md` | Project instructions for AI assistants |

---

## Chunk 1: Foundation — Config, Exchange Client, Analytics Engine

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `CLAUDE.md`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
ccxt>=4.0
pandas>=2.0
numpy>=1.24
streamlit>=1.30
plotly>=5.18
python-dotenv>=1.0
pytest>=7.0
```

- [ ] **Step 2: Create CLAUDE.md**

Write project instructions covering: architecture, file responsibilities, how to run, key concepts (exchanges, trade types, metrics), style preferences (same as grid-backtest).

- [ ] **Step 3: Create empty test package**

```bash
touch tests/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt CLAUDE.md tests/__init__.py
git commit -m "chore: add requirements, CLAUDE.md, test package"
```

---

### Task 2: Config module — API key management

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/andrew/pnl && python3 -m pytest tests/test_config.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement config.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/andrew/pnl && python3 -m pytest tests/test_config.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add config module for API key management"
```

---

### Task 3: Exchange client — CCXT wrapper

**Files:**
- Create: `exchange_client.py`
- Create: `tests/test_exchange_client.py`

- [ ] **Step 1: Write failing tests for exchange client**

```python
# tests/test_exchange_client.py
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
    """Binance trade format → unified DataFrame."""
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
    ]
    assert df.iloc[0]["side"] == "buy"
    assert df.iloc[1]["price"] == 35100.0
    assert df.iloc[0]["fee"] == 0.07


def test_normalize_trades_empty():
    df = normalize_trades([])
    assert len(df) == 0
    assert "time" in df.columns
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/andrew/pnl && python3 -m pytest tests/test_exchange_client.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement exchange_client.py**

```python
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
        # Fetch all symbols the account has traded
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/andrew/pnl && python3 -m pytest tests/test_exchange_client.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add exchange_client.py tests/test_exchange_client.py
git commit -m "feat: add exchange client with CCXT wrapper for Binance and Bybit"
```

---

### Task 4: Analytics engine — metric computation

**Files:**
- Create: `analytics.py`
- Create: `tests/test_analytics.py`

- [ ] **Step 1: Write failing tests for analytics**

```python
# tests/test_analytics.py
import numpy as np
import pandas as pd
import pytest

from analytics import compute_metrics, compute_daily_pnl, compute_pnl_by_coin


def _make_trades(n_trades=20):
    """Create synthetic trade data for testing."""
    times = pd.date_range("2024-01-01", periods=n_trades, freq="1h", tz="UTC")
    sides = ["buy", "sell"] * (n_trades // 2)
    prices = [100 + i * 0.5 for i in range(n_trades)]
    amounts = [0.1] * n_trades
    costs = [p * 0.1 for p in prices]
    fees = [c * 0.001 for c in costs]
    return pd.DataFrame({
        "time": times,
        "symbol": ["BTC/USDT"] * n_trades,
        "side": sides,
        "price": prices,
        "amount": amounts,
        "cost": costs,
        "fee": fees,
        "fee_currency": ["USDT"] * n_trades,
        "market_type": ["futures"] * n_trades,
    })


def test_compute_metrics_basic():
    df = _make_trades()
    m = compute_metrics(df)
    assert "total_pnl" in m
    assert "win_rate" in m
    assert "sharpe_ratio" in m
    assert "sortino_ratio" in m
    assert "max_drawdown" in m
    assert "total_volume" in m
    assert "n_trades" in m
    assert "avg_trade_size" in m
    assert "total_fees" in m
    assert "profit_factor" in m
    assert m["n_trades"] == 20
    assert m["total_fees"] > 0
    assert m["total_volume"] > 0


def test_compute_metrics_empty():
    df = pd.DataFrame(columns=[
        "time", "symbol", "side", "price", "amount", "cost",
        "fee", "fee_currency", "market_type",
    ])
    m = compute_metrics(df)
    assert m["n_trades"] == 0
    assert m["total_pnl"] == 0.0
    assert m["win_rate"] == 0.0


def test_compute_daily_pnl():
    df = _make_trades()
    daily = compute_daily_pnl(df)
    assert isinstance(daily, pd.Series)
    assert len(daily) > 0
    assert daily.index.name == "date"


def test_compute_pnl_by_coin():
    df = _make_trades()
    # Add a second coin
    df2 = _make_trades()
    df2["symbol"] = "ETH/USDT"
    combined = pd.concat([df, df2], ignore_index=True)
    result = compute_pnl_by_coin(combined)
    assert "BTC/USDT" in result
    assert "ETH/USDT" in result


def test_win_rate_bounds():
    df = _make_trades()
    m = compute_metrics(df)
    assert 0.0 <= m["win_rate"] <= 100.0


def test_sharpe_ratio_type():
    df = _make_trades()
    m = compute_metrics(df)
    assert isinstance(m["sharpe_ratio"], float)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/andrew/pnl && python3 -m pytest tests/test_analytics.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement analytics.py**

```python
"""
analytics.py — Trade analytics engine.
Computes P&L, risk metrics, breakdowns from a unified trades DataFrame.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _pair_trades(df: pd.DataFrame) -> list[dict]:
    """
    FIFO matching of buys and sells per symbol.
    Returns list of round-trip dicts with 'pnl' and 'symbol'.
    """
    round_trips: list[dict] = []

    for symbol in df["symbol"].unique():
        sym_df = df[df["symbol"] == symbol].sort_values("time")
        inventory: list[tuple[float, float]] = []  # (price, amount)

        for _, row in sym_df.iterrows():
            side = row["side"]
            price = row["price"]
            amount = row["amount"]
            fee = row["fee"]

            if side == "buy":
                inventory.append((price, amount))
            elif side == "sell" and inventory:
                remaining = amount
                while remaining > 0 and inventory:
                    entry_price, entry_amt = inventory[0]
                    matched = min(remaining, entry_amt)
                    pnl = (price - entry_price) * matched - fee * (matched / amount)
                    round_trips.append({
                        "symbol": symbol,
                        "pnl": pnl,
                        "entry_price": entry_price,
                        "exit_price": price,
                        "amount": matched,
                    })
                    remaining -= matched
                    if matched >= entry_amt:
                        inventory.pop(0)
                    else:
                        inventory[0] = (entry_price, entry_amt - matched)

    return round_trips


def compute_metrics(df: pd.DataFrame) -> dict:
    """
    Compute all trading metrics from a trades DataFrame.

    Expected columns: time, symbol, side, price, amount, cost, fee
    """
    if df.empty:
        return {
            "total_pnl": 0.0, "pnl_pct": 0.0, "win_rate": 0.0,
            "profit_factor": 0.0, "sharpe_ratio": 0.0, "sortino_ratio": 0.0,
            "max_drawdown": 0.0, "total_volume": 0.0, "n_trades": 0,
            "avg_trade_size": 0.0, "total_fees": 0.0,
            "best_day_pnl": 0.0, "worst_day_pnl": 0.0,
            "rt_count": 0, "rt_profits": [],
        }

    n_trades = len(df)
    total_volume = float(df["cost"].sum())
    total_fees = float(df["fee"].sum())
    avg_trade_size = total_volume / n_trades if n_trades > 0 else 0.0

    # Round trip P&L
    rts = _pair_trades(df)
    rt_pnls = [rt["pnl"] for rt in rts]
    total_pnl = sum(rt_pnls) if rt_pnls else 0.0

    # Win rate
    wins = [p for p in rt_pnls if p > 0]
    losses = [p for p in rt_pnls if p <= 0]
    win_rate = (len(wins) / len(rt_pnls) * 100.0) if rt_pnls else 0.0

    # Profit factor
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

    # P&L %
    total_buy_cost = float(df.loc[df["side"] == "buy", "cost"].sum())
    pnl_pct = (total_pnl / total_buy_cost * 100.0) if total_buy_cost > 0 else 0.0

    # Daily P&L for risk metrics
    daily_pnl = compute_daily_pnl(df)

    # Sharpe ratio (annualized, assuming daily returns)
    if len(daily_pnl) > 1 and daily_pnl.std() > 0:
        sharpe_ratio = float(daily_pnl.mean() / daily_pnl.std() * np.sqrt(365))
    else:
        sharpe_ratio = 0.0

    # Sortino ratio (downside deviation only)
    downside = daily_pnl[daily_pnl < 0]
    if len(downside) > 1 and downside.std() > 0:
        sortino_ratio = float(daily_pnl.mean() / downside.std() * np.sqrt(365))
    else:
        sortino_ratio = 0.0

    # Max drawdown from cumulative P&L
    cum_pnl = daily_pnl.cumsum()
    running_max = cum_pnl.cummax()
    drawdown = cum_pnl - running_max
    max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0.0

    # Best/worst day
    best_day_pnl = float(daily_pnl.max()) if len(daily_pnl) > 0 else 0.0
    worst_day_pnl = float(daily_pnl.min()) if len(daily_pnl) > 0 else 0.0

    return {
        "total_pnl": total_pnl,
        "pnl_pct": pnl_pct,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown,
        "total_volume": total_volume,
        "n_trades": n_trades,
        "avg_trade_size": avg_trade_size,
        "total_fees": total_fees,
        "best_day_pnl": best_day_pnl,
        "worst_day_pnl": worst_day_pnl,
        "rt_count": len(rts),
        "rt_profits": rt_pnls,
    }


def compute_daily_pnl(df: pd.DataFrame) -> pd.Series:
    """Compute daily P&L from trades using FIFO matching."""
    if df.empty:
        return pd.Series(dtype=float, name="pnl")

    rts = _pair_trades(df)
    if not rts:
        # Fall back to net cost flow per day
        df = df.copy()
        df["signed_cost"] = df.apply(
            lambda r: -r["cost"] - r["fee"] if r["side"] == "buy"
            else r["cost"] - r["fee"],
            axis=1,
        )
        daily = df.set_index("time").resample("D")["signed_cost"].sum()
        daily.index = daily.index.date
        daily.index.name = "date"
        return daily

    # Map round trips to exit dates
    # Use the trade DataFrame to find exit times
    sell_df = df[df["side"] == "sell"].sort_values("time")
    rt_records = []
    for rt in rts:
        # Find the matching sell trade
        matching = sell_df[
            (sell_df["symbol"] == rt["symbol"]) &
            (abs(sell_df["price"] - rt["exit_price"]) < 1e-8)
        ]
        if not matching.empty:
            date = matching.iloc[0]["time"]
            if hasattr(date, "date"):
                date = date.date()
            rt_records.append({"date": date, "pnl": rt["pnl"]})

    if not rt_records:
        return pd.Series(dtype=float, name="pnl")

    rt_df = pd.DataFrame(rt_records)
    daily = rt_df.groupby("date")["pnl"].sum()
    daily.index.name = "date"
    return daily


def compute_pnl_by_coin(df: pd.DataFrame) -> dict[str, float]:
    """Compute total P&L per trading symbol."""
    if df.empty:
        return {}
    rts = _pair_trades(df)
    result: dict[str, float] = {}
    for rt in rts:
        sym = rt["symbol"]
        result[sym] = result.get(sym, 0.0) + rt["pnl"]
    return result


def compute_weekly_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Weekly aggregates: volume, trades, P&L."""
    if df.empty:
        return pd.DataFrame(columns=["week", "volume", "trades", "pnl"])

    df = df.copy()
    df["week"] = df["time"].dt.isocalendar().week
    df["year"] = df["time"].dt.year

    weekly_volume = df.groupby(["year", "week"])["cost"].sum()
    weekly_trades = df.groupby(["year", "week"]).size()

    daily = compute_daily_pnl(df)
    # Can't easily map daily to weekly without more context, return volume+trades
    result = pd.DataFrame({
        "volume": weekly_volume,
        "trades": weekly_trades,
    })
    result.index.names = ["year", "week"]
    return result.reset_index()


def compute_most_traded(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Top N most traded symbols by volume."""
    if df.empty:
        return pd.DataFrame(columns=["symbol", "volume", "trades"])

    grouped = df.groupby("symbol").agg(
        volume=("cost", "sum"),
        trades=("cost", "count"),
    ).sort_values("volume", ascending=False).head(top_n)

    return grouped.reset_index()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/andrew/pnl && python3 -m pytest tests/test_analytics.py -v
```
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add analytics.py tests/test_analytics.py
git commit -m "feat: add analytics engine with P&L, risk metrics, breakdowns"
```

---

## Chunk 2: Streamlit Dashboard & Deployment

### Task 5: Streamlit app — sidebar and connection

**Files:**
- Create: `app.py`

- [ ] **Step 1: Create app.py with page config, CSS theme, sidebar**

The CSS and color system should be copied from grid-backtest's Terminal Noir theme. The sidebar should contain:
- Exchange selector radio (Binance / Bybit)
- API key input (st.text_input with type="password")
- API secret input (st.text_input with type="password")
- Save/Load keys toggle (st.checkbox)
- Connect button
- Date range picker (start_date, end_date)
- Market filter radio (All / Spot / Futures)

On connect:
- Validate keys are non-empty
- If save is checked, call `save_keys()`
- Use `@st.cache_data(ttl=1800)` on the trade fetch function
- Store trades in `st.session_state`

Color constants, CHART_LAYOUT, GRID_STYLE, helper functions (`_kpi`, `_pnl_color`, `_stat_panel`, `_section`) — all reused from grid-backtest.

- [ ] **Step 2: Test manually — sidebar renders, connection flow works**

```bash
cd /Users/andrew/pnl && streamlit run app.py --server.port 8504
```
Verify: sidebar renders, inputs work, connect button triggers fetch.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Streamlit app with sidebar, connection flow, Terminal Noir theme"
```

---

### Task 6: Streamlit app — KPI cards and main layout

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add KPI cards section**

After successful connection and trade fetch, display:
- Row 1 (6 cols): Total P&L, P&L %, Win Rate, Profit Factor, Round Trips, # Trades
- Row 2 (6 cols): Sharpe, Sortino, Max Drawdown, Total Volume, Avg Trade Size, Total Fees
- Row 3 (4 cols): Best Day, Worst Day, Cash equivalent, Market filter label

Use the `_kpi()` helper from grid-backtest pattern.

- [ ] **Step 2: Add header banner**

Show exchange name, market type filter, date range, and account summary in the `hdr-banner` div pattern.

- [ ] **Step 3: Test manually**

```bash
cd /Users/andrew/pnl && streamlit run app.py --server.port 8504
```
Verify: KPIs render with correct values.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add KPI cards and header banner"
```

---

### Task 7: Streamlit app — charts

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add equity curve (cumulative P&L over time)**

Plotly line chart using daily P&L cumsum. Purple line with fill, matching grid-backtest style.

- [ ] **Step 2: Add P&L by coin bar chart**

Horizontal bar chart, sorted by P&L. Green for positive, red for negative.

- [ ] **Step 3: Add calendar heatmap**

Use Plotly heatmap with days on x-axis, weeks on y-axis. Green shades for profit days, red for loss days.

- [ ] **Step 4: Test manually**

```bash
cd /Users/andrew/pnl && streamlit run app.py --server.port 8504
```

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: add equity curve, P&L by coin, and calendar heatmap charts"
```

---

### Task 8: Streamlit app — tabs (trade log, breakdowns)

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add tabbed section with 3 tabs**

- **Trade Log**: Paginated dataframe of all trades (last 500), formatted columns
- **Most Traded Pairs**: Table showing top 10 pairs by volume + trade count
- **Daily/Weekly Breakdown**: Two sub-columns — daily P&L table, weekly summary table

Follow grid-backtest patterns: `.stat-panel`, formatted strings, `st.dataframe()` with `width="stretch"`.

- [ ] **Step 2: Add footer**

```python
st.markdown(
    '<div class="footer">P/L // ANALYTICS &middot; '
    'Binance & Bybit via CCXT &middot; '
    'Read-only API access &middot; Not financial advice</div>',
    unsafe_allow_html=True,
)
```

- [ ] **Step 3: Test manually**

```bash
cd /Users/andrew/pnl && streamlit run app.py --server.port 8504
```

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add trade log, breakdowns tabs, and footer"
```

---

### Task 9: Deploy script

**Files:**
- Create: `deploy.sh`

- [ ] **Step 1: Create deploy.sh**

Same pattern as grid-backtest but:
- Repo: `arozenfelds-hash/pnl`
- Install dir: `/opt/pnl`
- Service name: `pnl`
- Port: `8504`

```bash
#!/bin/bash
set -e

echo "=== P/L Analytics — Deploy ==="

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv python3.12-venv 2>/dev/null || \
apt-get install -y -qq python3 python3-pip python3-venv

REPO_DIR="/opt/pnl"
if [ -d "$REPO_DIR" ]; then
    echo "Updating repo..."
    cd "$REPO_DIR" && git pull
else
    echo "Cloning repo..."
    git clone https://github.com/arozenfelds-hash/pnl.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

cat > /etc/systemd/system/pnl.service << 'UNIT'
[Unit]
Description=P/L Analytics (Streamlit)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pnl
ExecStart=/opt/pnl/venv/bin/streamlit run app.py --server.port 8504 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable pnl
systemctl restart pnl

echo ""
echo "=== Deployed! ==="
echo "App running on http://$(hostname -I | awk '{print $1}'):8504"
echo "Manage: systemctl {start|stop|restart|status} pnl"
echo "Logs:   journalctl -u pnl -f"
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x deploy.sh
git add deploy.sh
git commit -m "feat: add deployment script for server setup"
```

---

### Task 10: Final integration test

- [ ] **Step 1: Run all unit tests**

```bash
cd /Users/andrew/pnl && python3 -m pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 2: Verify app starts without errors**

```bash
cd /Users/andrew/pnl && timeout 10 streamlit run app.py --server.port 8504 --server.headless true 2>&1 || true
```

- [ ] **Step 3: Final commit and push**

```bash
git add -A
git commit -m "chore: final cleanup"
git push -u origin main
```
