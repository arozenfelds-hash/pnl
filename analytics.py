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
            "max_drawdown": 0.0, "total_volume": 0.0, "turnover": 0.0, "n_trades": 0,
            "avg_trade_size": 0.0, "total_fees": 0.0,
            "best_day_pnl": 0.0, "worst_day_pnl": 0.0,
            "rt_count": 0, "rt_profits": [],
        }

    n_trades = len(df)
    total_volume = float(df["cost"].sum())
    turnover = total_volume * 2  # both sides (open + close), matches exchange reporting
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
        "turnover": turnover,
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
    sell_df = df[df["side"] == "sell"].sort_values("time")
    rt_records = []
    for rt in rts:
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


def estimate_daily_balance(
    df: pd.DataFrame,
    current_balance: float,
    end_date=None,
    transfers_df: pd.DataFrame | None = None,
) -> pd.Series:
    """
    Estimate daily USDT balance by working backwards from current balance.
    Uses daily P&L from round-trip matching (works for futures + spot).
    initial_balance = current_balance - total_pnl - net_transfers

    Parameters
    ----------
    df             : trades DataFrame
    current_balance: current total USDT balance (from exchange API)
    end_date       : date of the current balance (defaults to today)
    transfers_df   : deposits/withdrawals DataFrame (from fetch_deposits_withdrawals)

    Returns
    -------
    pd.Series with date index and estimated USDT balance values.
    """
    if df.empty:
        return pd.Series(dtype=float, name="balance")

    # Use daily P&L from round-trip matching (accurate for futures + spot)
    daily_pnl = compute_daily_pnl(df)

    df = df.copy()
    df["date"] = pd.to_datetime(df["time"]).dt.date

    # Deposit/withdrawal flows
    daily_transfers = pd.Series(dtype=float)
    if transfers_df is not None and not transfers_df.empty:
        tf = transfers_df.copy()
        tf["date"] = pd.to_datetime(tf["time"]).dt.date
        tf = tf[tf["status"].isin(["ok", "successful", "completed", "success"])]
        if not tf.empty:
            tf["transfer_flow"] = tf.apply(
                lambda r: r["amount"] if r["type"] == "deposit" else -r["amount"],
                axis=1,
            )
            daily_transfers = tf.groupby("date")["transfer_flow"].sum()

    if end_date is None:
        end_date = pd.Timestamp.now(tz="UTC").date()

    # Build date range
    start_dates = [df["date"].min()]
    if len(daily_pnl) > 0:
        start_dates.append(min(daily_pnl.index))
    if len(daily_transfers) > 0:
        start_dates.append(min(daily_transfers.index))

    all_dates = pd.date_range(start=min(start_dates), end=end_date, freq="D")
    date_index = all_dates.date

    # Align daily P&L to full date range
    full_pnl = pd.Series(0.0, index=date_index, name="pnl")
    for d, v in daily_pnl.items():
        if d in full_pnl.index:
            full_pnl[d] = v

    full_transfers = pd.Series(0.0, index=date_index, name="transfers")
    for d, v in daily_transfers.items():
        if d in full_transfers.index:
            full_transfers[d] = v

    # initial_balance = current_balance - total_pnl - net_transfers
    total_pnl = full_pnl.sum()
    net_transfers = full_transfers.sum()
    initial_balance = current_balance - total_pnl - net_transfers

    # Build balance forward: initial + cumsum(daily_pnl + transfers)
    daily_change = full_pnl + full_transfers
    balance = initial_balance + daily_change.cumsum()

    balance.index.name = "date"
    balance.name = "balance"
    return balance
