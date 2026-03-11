import numpy as np
import pandas as pd
import pytest

from analytics import compute_metrics, compute_daily_pnl, compute_pnl_by_coin, estimate_daily_balance


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


def test_estimate_daily_balance():
    df = _make_trades()
    balance = estimate_daily_balance(df, current_balance=5000.0)
    assert isinstance(balance, pd.Series)
    assert len(balance) > 0
    assert balance.name == "balance"
    # Last value should be close to current_balance
    assert abs(balance.iloc[-1] - 5000.0) < 1.0


def test_estimate_daily_balance_empty():
    df = pd.DataFrame(columns=[
        "time", "symbol", "side", "price", "amount", "cost",
        "fee", "fee_currency", "market_type",
    ])
    balance = estimate_daily_balance(df, current_balance=1000.0)
    assert isinstance(balance, pd.Series)
    assert len(balance) == 0
