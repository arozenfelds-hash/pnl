# P/L — Exchange Account Analytics Dashboard

## Overview
Connect read-only API keys from Binance and/or Bybit to view comprehensive
account statistics for any selected period. Streamlit dashboard with Terminal
Noir aesthetic (matching grid-backtest).

## Architecture

```
pnl/
├── app.py              # Streamlit dashboard (UI, charts, KPIs)
├── exchange_client.py  # CCXT wrapper — connect, fetch trades, balances
├── analytics.py        # Compute all metrics from raw trade data
├── config.py           # API key management (save/load from ~/.pnl/config.env)
├── requirements.txt
├── .gitignore
└── deploy.sh
```

## Data Flow

1. User enters API keys (read-only) + selects exchange (Binance/Bybit)
2. `exchange_client.py` fetches trade history (spot + futures) and current balances
3. `analytics.py` computes all metrics from raw trades for selected time period
4. `app.py` displays everything in Terminal Noir theme

## Exchange Support
- **Binance**: spot + USDM futures via `ccxt.binance` / `ccxt.binanceusdm`
- **Bybit**: spot + derivatives via `ccxt.bybit`
- Unified interface through CCXT — same code path for both exchanges

## API Key Management
- Option A: Enter keys per session in sidebar (password fields, no storage)
- Option B: Save keys to `~/.pnl/config.env` (outside repo, persistent)
- Toggle in sidebar to choose mode
- Only read-only permissions required; validated on connect

## UI Layout

### Sidebar
- Exchange selector (Binance / Bybit)
- API key + secret inputs (password fields)
- Save/load keys toggle
- Date range picker (period selection)
- Market filter (All / Spot / Futures)

### Main Area
- Header banner with exchange name + account summary
- KPI row 1: Total P&L, P&L %, Win Rate, Profit Factor
- KPI row 2: Sharpe, Sortino, Max Drawdown, Total Volume
- KPI row 3: # Trades, Avg Trade Size, Fees Paid, Best/Worst Day
- Equity curve chart (cumulative P&L over time)
- P&L by coin (bar chart)
- Calendar heatmap (daily P&L)
- Tabs: Trade Log, Most Traded Pairs, Daily/Weekly Breakdown

## Metrics

| Category | Metrics |
|----------|---------|
| Core | Total P&L ($), P&L %, win rate, profit factor |
| Risk | Sharpe ratio, Sortino ratio, max drawdown |
| Activity | # trades, avg trade size, total volume, fees paid |
| Breakdown | P&L by coin, daily/weekly aggregates, most traded pairs |

## Deployment
- Streamlit on port 8504
- Systemd service via deploy.sh (same pattern as grid-backtest)

## Dependencies
- ccxt, pandas, numpy, streamlit, plotly
