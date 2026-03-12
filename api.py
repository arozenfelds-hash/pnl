"""
api.py — FastAPI backend for P/L Analytics.
Exposes REST endpoints wrapping exchange_client.py, analytics.py, config.py.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analytics import (
    compute_daily_pnl,
    compute_metrics,
    compute_most_traded,
    compute_pnl_by_coin,
    compute_weekly_breakdown,
    estimate_daily_balance,
)
from config import (
    delete_account,
    get_account,
    list_accounts,
    load_balance_snapshots,
    save_account,
    save_balance_snapshot,
)
from exchange_client import (
    fetch_all_trades,
    fetch_balance,
    fetch_deposits_withdrawals,
    fetch_positions,
)

app = FastAPI(title="P/L Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response models ─────────────────────────────────────────────────


class ConnectRequest(BaseModel):
    account_name: str
    exchange: str
    api_key: str
    api_secret: str
    start_date: str  # ISO date, e.g. "2025-01-01"
    end_date: str
    market_filter: str = "all"  # all | spot | futures
    save_account: bool = False


class AccountRequest(BaseModel):
    name: str
    exchange: str
    api_key: str
    api_secret: str


# ── Accounts ────────────────────────────────────────────────────────────────


@app.get("/api/accounts")
def api_list_accounts():
    names = list_accounts()
    accounts = []
    for name in names:
        acct = get_account(name)
        if acct:
            snapshots = load_balance_snapshots(name)
            last_bal = snapshots[-1]["balance_usdt"] if snapshots else None
            accounts.append({
                "name": name,
                "exchange": acct["exchange"],
                "last_balance": last_bal,
            })
    return {"accounts": accounts}


@app.post("/api/accounts")
def api_save_account(req: AccountRequest):
    save_account(req.name, req.exchange, api_key, api_secret)
    return {"ok": True}


@app.delete("/api/accounts/{name}")
def api_delete_account(name: str):
    delete_account(name)
    return {"ok": True}


# ── Main data endpoint ──────────────────────────────────────────────────────


@app.post("/api/connect")
def api_connect(req: ConnectRequest):
    """Fetch all data for an account: trades, balance, positions, transfers, metrics."""
    exchange_id = req.exchange.lower()
    api_key = req.api_key
    api_secret = req.api_secret

    # For saved accounts, load keys from server config
    if api_key == "__saved__":
        acct = get_account(req.account_name)
        if not acct:
            raise HTTPException(status_code=404, detail="Account not found")
        exchange_id = acct["exchange"]
        api_key = acct["api_key"]
        api_secret = acct["api_secret"]

    since_ms = int(pd.Timestamp(req.start_date, tz="UTC").timestamp() * 1000)
    end_ts = pd.Timestamp(req.end_date, tz="UTC") + pd.Timedelta(days=1)

    if req.save_account:
        save_account(req.account_name, exchange_id, api_key, api_secret)

    # Trades
    try:
        trades_df = fetch_all_trades(
            exchange_id, api_key, api_secret,
            since_ms=since_ms, account_name=req.account_name,
            market_filter=req.market_filter,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trades: {e}")

    if not trades_df.empty:
        trades_df = trades_df[trades_df["time"] < end_ts]

    # Balance
    bal_info = {"total_usdt": 0, "spot_usdt": 0, "futures_usdt": 0,
                "account_a_label": "Spot", "account_b_label": "Futures"}
    try:
        bal_info = fetch_balance(exchange_id, api_key, api_secret)
        save_balance_snapshot(req.account_name, bal_info["total_usdt"])
    except Exception:
        pass

    # Positions
    positions = []
    try:
        pos_df = fetch_positions(exchange_id, api_key, api_secret)
        if not pos_df.empty:
            positions = pos_df.to_dict("records")
    except Exception:
        pass

    # Transfers
    transfers = []
    transfers_df = None
    try:
        transfers_df = fetch_deposits_withdrawals(
            exchange_id, api_key, api_secret, since_ms=since_ms,
        )
        if not transfers_df.empty:
            tf = transfers_df.copy()
            tf["time"] = tf["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")
            transfers = tf.to_dict("records")
    except Exception:
        pass

    # Market filter
    filtered_df = trades_df
    if req.market_filter == "spot":
        filtered_df = trades_df[trades_df["market_type"] == "spot"]
    elif req.market_filter == "futures":
        filtered_df = trades_df[trades_df["market_type"] == "futures"]

    # Metrics
    metrics = compute_metrics(filtered_df)
    rt_profits = metrics.pop("rt_profits", [])

    # Daily PnL
    daily_pnl = compute_daily_pnl(filtered_df)
    daily_pnl_list = [
        {"date": str(d), "pnl": float(v)} for d, v in daily_pnl.items()
    ]

    # PnL by coin
    pnl_by_coin = compute_pnl_by_coin(filtered_df)
    pnl_by_coin_list = [
        {"symbol": s, "pnl": float(v)}
        for s, v in sorted(pnl_by_coin.items(), key=lambda x: x[1], reverse=True)
    ]

    # Weekly breakdown
    weekly = compute_weekly_breakdown(filtered_df)
    weekly_list = weekly.to_dict("records") if not weekly.empty else []

    # Most traded
    most_traded = compute_most_traded(filtered_df)
    most_traded_list = []
    if not most_traded.empty:
        for _, row in most_traded.iterrows():
            most_traded_list.append({
                "symbol": row["symbol"],
                "volume": float(row["volume"]),
                "trades": int(row["trades"]),
                "pnl": pnl_by_coin.get(row["symbol"], 0.0),
            })

    # Balance history
    balance_history = []
    current_balance = bal_info["total_usdt"]
    if current_balance and not filtered_df.empty:
        bal_series = estimate_daily_balance(
            filtered_df, current_balance, pd.Timestamp(req.end_date).date(),
            transfers_df,
        )
        balance_history = [
            {"date": str(d), "balance": float(v)} for d, v in bal_series.items()
        ]

    # Snapshots
    snapshots = load_balance_snapshots(req.account_name)
    snap_list = [
        {"time": s["time"], "balance": s["balance_usdt"]} for s in snapshots
    ]

    # Trade log (last 500)
    trade_log = []
    if not filtered_df.empty:
        log_df = filtered_df.tail(500).copy()
        for _, row in log_df.iterrows():
            side = row.get("side", "")
            market = row.get("market_type", "")
            reduce = row.get("reduce_only", False)
            if market == "futures":
                if side == "buy":
                    action = "Close Short" if reduce else "Open Long"
                elif side == "sell":
                    action = "Close Long" if reduce else "Open Short"
                else:
                    action = side
            else:
                action = side

            trade_log.append({
                "time": row["time"].strftime("%Y-%m-%d %H:%M"),
                "symbol": row["symbol"],
                "action": action,
                "price": float(row["price"]),
                "amount": float(row["amount"]),
                "cost": float(row["cost"]),
                "fee": float(row["fee"]),
                "market_type": market,
            })

    total_trades = len(filtered_df)

    return {
        "balance": {
            "total": bal_info["total_usdt"],
            "account_a": bal_info["spot_usdt"],
            "account_b": bal_info["futures_usdt"],
            "label_a": bal_info["account_a_label"],
            "label_b": bal_info["account_b_label"],
        },
        "metrics": metrics,
        "daily_pnl": daily_pnl_list,
        "pnl_by_coin": pnl_by_coin_list,
        "weekly": weekly_list,
        "most_traded": most_traded_list,
        "positions": positions,
        "transfers": transfers,
        "balance_history": balance_history,
        "snapshots": snap_list,
        "trade_log": trade_log,
        "total_trades": total_trades,
        "initial_balance": balance_history[0]["balance"] if balance_history else None,
        "coins_traded": len(pnl_by_coin),
    }


# Serve frontend static files in production
DIST_DIR = Path(__file__).parent / "frontend" / "dist"
if DIST_DIR.exists():
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file = DIST_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(DIST_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8505)
