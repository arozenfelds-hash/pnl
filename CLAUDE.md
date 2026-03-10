# P/L — Exchange Account Analytics

## Project Overview
Streamlit dashboard that connects to Binance and Bybit via read-only API keys
and displays comprehensive trading account analytics for any selected period.
Terminal Noir aesthetic (matching grid-backtest project).

## Architecture

```
pnl/
├── app.py              # Streamlit dashboard (UI, charts, KPIs)
├── exchange_client.py  # CCXT wrapper — connect, fetch trades, balances
├── analytics.py        # Compute all metrics from raw trade data
├── config.py           # API key management (save/load from ~/.pnl/config.env)
├── tests/              # pytest test suite
├── requirements.txt
├── deploy.sh
└── docs/               # Specs and plans
```

## Key Concepts

### Exchanges
- **Binance**: spot (`ccxt.binance`) + USDM futures (`ccxt.binanceusdm`)
- **Bybit**: spot + derivatives (`ccxt.bybit`)
- Unified interface through CCXT

### Trade Data
- Fetched via `exchange.fetch_my_trades()` with pagination
- Normalized to unified DataFrame: time, symbol, side, price, amount, cost, fee
- `market_type` column distinguishes spot vs futures

### Metrics
- **Core**: Total P&L, P&L %, win rate, profit factor
- **Risk**: Sharpe ratio, Sortino ratio, max drawdown
- **Activity**: # trades, avg trade size, total volume, fees paid
- **Breakdown**: P&L by coin, daily/weekly aggregates, most traded pairs

### API Key Security
- Keys stored in `~/.pnl/config.env` (outside repo)
- Only read-only permissions required
- Option to enter per-session (no storage) or save locally

## Common Tasks

### Run the app
```bash
cd ~/pnl && streamlit run app.py --server.port 8504
```

### Run tests
```bash
cd ~/pnl && python3 -m pytest tests/ -v
```

## Style Preferences
- Use `width="stretch"` not `use_container_width=True` (Streamlit deprecation)
- All values in dataframes should be `str` type to avoid Arrow serialization errors
- Terminal Noir theme: dark backgrounds, DM Mono font, Outfit headings
- Colors: cyan (#00d4ff), green (#00e68a), red (#ff3b5c), purple (#a855f7), amber (#f59e0b)

## Dependencies
- `ccxt` (Binance + Bybit)
- `pandas`, `numpy` (data + computation)
- `streamlit` (dashboard)
- `plotly` (charts)
- `python-dotenv` (config)
