"""
app.py
======
P/L Exchange Analytics — Streamlit Dashboard.
Terminal Noir aesthetic — Bloomberg meets cyberpunk.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

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
from exchange_client import fetch_all_trades, fetch_balance

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="P/L // Analytics",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Color system ──────────────────────────────────────────────────────────────
C_BG       = "#06080d"
C_SURFACE  = "#0c1018"
C_BORDER   = "#1a1f2e"
C_BORDER2  = "#252b3b"
C_TEXT     = "#c8d1dc"
C_MUTED    = "#5a6578"
C_GREEN    = "#00e68a"
C_RED      = "#ff3b5c"
C_CYAN     = "#00d4ff"
C_PURPLE   = "#a855f7"
C_AMBER    = "#f59e0b"
C_BLUE     = "#3b82f6"

# ── Chart theme ──────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(6,8,13,0.6)",
    font=dict(family="DM Mono, monospace", color=C_MUTED, size=10),
    margin=dict(l=0, r=12, t=28, b=0),
    legend=dict(
        bgcolor="rgba(12,16,24,0.9)", bordercolor=C_BORDER, borderwidth=1,
        orientation="h", x=0, y=1.02, font=dict(size=9, color=C_MUTED),
    ),
)
GRID_STYLE = dict(showgrid=True, gridcolor="rgba(26,31,46,0.6)", gridwidth=1,
                   zeroline=False)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;500;600;700;800&display=swap');

:root {{
    --bg: {C_BG}; --surface: {C_SURFACE}; --border: {C_BORDER};
    --text: {C_TEXT}; --muted: {C_MUTED};
    --green: {C_GREEN}; --red: {C_RED}; --cyan: {C_CYAN};
    --purple: {C_PURPLE}; --amber: {C_AMBER}; --blue: {C_BLUE};
}}

html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"], .main .block-container {{
    background-color: var(--bg) !important;
    color: var(--text);
    font-family: 'DM Mono', monospace;
}}

[data-testid="stAppViewContainer"]::before {{
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
        radial-gradient(ellipse 80% 50% at 20% 0%, rgba(0,212,255,0.03) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(168,85,247,0.03) 0%, transparent 60%);
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #080c14 0%, #0a0e18 50%, #080c14 100%) !important;
    border-right: 1px solid var(--border) !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdown"] h1 {{
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important; letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-size: 1.5rem !important; margin-bottom: 0 !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdown"] h3 {{
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important; letter-spacing: 0.06em;
    text-transform: uppercase; font-size: 0.65rem !important;
    color: var(--muted) !important; margin-bottom: 4px !important;
}}
[data-testid="stSidebar"] hr {{ border-color: var(--border) !important; opacity: 0.5; }}
[data-testid="stSidebar"] label {{
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important; color: var(--muted) !important;
}}
[data-testid="stSidebar"] .stRadio > div {{
    gap: 0.5rem !important;
}}
[data-testid="stSidebar"] .stTextInput input {{
    background: rgba(12,16,24,0.8) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important;
}}
[data-testid="stSidebar"] .stDateInput input {{
    background: rgba(12,16,24,0.8) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important;
}}

/* Main content headings */
.main h2, .main h3 {{
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}}

/* Section divider */
hr.noir {{ border: none; border-top: 1px solid var(--border); margin: 28px 0; }}

/* Dataframes */
[data-testid="stDataFrame"] {{
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    overflow: hidden;
}}

/* KPI Cards */
.kpi {{
    background: linear-gradient(135deg, rgba(12,16,24,0.95), rgba(18,24,36,0.9));
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 12px 14px;
    text-align: center;
    position: relative;
    overflow: hidden;
    min-height: 96px;
    display: flex; flex-direction: column; justify-content: center;
}}
.kpi::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: var(--accent-color, var(--cyan));
    opacity: 0.8;
}}
.kpi-val {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.3rem; font-weight: 700;
    line-height: 1.15;
    color: var(--accent-color, var(--cyan));
    text-shadow: 0 0 20px color-mix(in srgb, var(--accent-color, var(--cyan)) 30%, transparent);
}}
.kpi-lbl {{
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; font-weight: 400;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 6px;
}}

/* Header banner */
.hdr-banner {{
    background: linear-gradient(135deg, rgba(0,212,255,0.06) 0%, rgba(168,85,247,0.06) 50%, rgba(0,230,138,0.04) 100%);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px 16px;
    margin-bottom: 8px;
    position: relative;
    overflow: hidden;
}}
.hdr-banner::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--cyan), var(--purple), var(--green));
}}
.hdr-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.6rem; font-weight: 800;
    letter-spacing: -0.03em;
    color: #eef1f6;
    margin: 0;
}}
.hdr-badge {{
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; font-weight: 500;
    letter-spacing: 0.08em; text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 4px;
    margin-left: 12px;
    position: relative; top: -2px;
}}
.hdr-badge.binance {{
    background: rgba(245,158,11,0.12); color: var(--amber);
    border: 1px solid rgba(245,158,11,0.25);
}}
.hdr-badge.bybit {{
    background: rgba(0,212,255,0.12); color: var(--cyan);
    border: 1px solid rgba(0,212,255,0.25);
}}
.hdr-meta {{
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem; color: var(--muted);
    margin-top: 8px; line-height: 1.6;
}}
.hdr-meta span {{ color: var(--text); font-weight: 500; }}

/* Section headers */
.sec-hdr {{
    font-family: 'Outfit', sans-serif;
    font-weight: 700; font-size: 1.05rem;
    letter-spacing: -0.01em;
    color: #dde1e8;
    display: flex; align-items: center; gap: 10px;
    margin: 0 0 12px 0;
}}
.sec-hdr::after {{
    content: '';
    flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--border), transparent);
}}
.sec-dot {{
    display: inline-block; width: 6px; height: 6px;
    border-radius: 50%; margin-right: 2px;
}}

/* Stat rows */
.stat-panel {{
    background: linear-gradient(135deg, rgba(12,16,24,0.9), rgba(16,20,30,0.85));
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
}}
.stat-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0;
    border-bottom: 1px solid rgba(26,31,46,0.4);
    font-size: 0.78rem;
}}
.stat-row:last-child {{ border-bottom: none; }}
.stat-k {{ color: var(--muted); font-weight: 400; }}
.stat-v {{ color: var(--text); font-weight: 500; text-align: right; }}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0; background: transparent;
    border-bottom: 1px solid var(--border);
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--muted) !important;
    border-bottom: 2px solid transparent;
    padding: 8px 16px !important;
}}
.stTabs [aria-selected="true"] {{
    color: var(--cyan) !important;
    border-bottom-color: var(--cyan) !important;
    background: rgba(0,212,255,0.04) !important;
}}

/* Footer */
.footer {{
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem; color: var(--muted);
    text-align: center;
    padding: 24px 0 8px;
    border-top: 1px solid var(--border);
    margin-top: 32px;
}}

/* Hide streamlit defaults */
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent !important; }}
.block-container {{ padding-top: 2rem !important; padding-bottom: 0 !important; }}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _kpi(label: str, value: str, color: str = C_CYAN) -> str:
    return (
        f'<div class="kpi" style="--accent-color:{color}">'
        f'<div class="kpi-val">{value}</div>'
        f'<div class="kpi-lbl">{label}</div></div>'
    )

def _pnl_color(v: float) -> str:
    return C_GREEN if v >= 0 else C_RED

def _stat_panel(rows: list[tuple[str, str, str]]) -> str:
    """Build a stat panel. Each row = (key, value, color)."""
    inner = ""
    for k, v, c in rows:
        inner += f'<div class="stat-row"><span class="stat-k">{k}</span><span class="stat-v" style="color:{c}">{v}</span></div>'
    return f'<div class="stat-panel">{inner}</div>'

def _section(title: str, dot_color: str = C_CYAN) -> str:
    return f'<div class="sec-hdr"><span class="sec-dot" style="background:{dot_color}"></span>{title}</div>'


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("# P/L // Analytics")
    st.caption("Binance & Bybit Account Statistics")
    st.markdown("---")

    # ── Account management ────────────────────────────────────────────────
    st.markdown("### Account")
    saved_accounts = list_accounts()

    account_mode = st.radio("Mode", ["Saved Account", "New / Manual"], horizontal=True,
                             label_visibility="collapsed")

    if account_mode == "Saved Account" and saved_accounts:
        p_account_name = st.selectbox("Select Account", saved_accounts)
        acct = get_account(p_account_name)
        if acct:
            p_exchange = acct["exchange"].capitalize()
            exchange_id = acct["exchange"]
            p_api_key = acct["api_key"]
            p_api_secret = acct["api_secret"]
        else:
            p_exchange = "Binance"
            exchange_id = "binance"
            p_api_key = ""
            p_api_secret = ""

        # Delete button
        if st.button("Delete Account", type="secondary"):
            delete_account(p_account_name)
            st.rerun()
    else:
        if not saved_accounts:
            st.caption("No saved accounts yet.")

        st.markdown("### Exchange")
        p_exchange = st.radio("Exchange", ["Binance", "Bybit"], horizontal=True,
                               label_visibility="collapsed")
        exchange_id = p_exchange.lower()

        st.markdown("### API Keys")
        p_account_name = st.text_input("Account Name", placeholder="e.g. Main, Bot1, Bybit-DCA")
        p_api_key = st.text_input("API Key", type="password")
        p_api_secret = st.text_input("API Secret", type="password")

        p_save_account = st.checkbox("Save account", value=True,
                                      help="Save to ~/.pnl/accounts.json (outside repo)")

    st.markdown("---")

    st.markdown("### Period")
    _default_start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)).date()
    _default_end = pd.Timestamp.now(tz="UTC").date()
    p_start_date = st.date_input("Start Date", value=_default_start)
    p_end_date = st.date_input("End Date", value=_default_end)
    st.markdown("---")

    st.markdown("### Market")
    p_market = st.radio("Market Filter", ["All", "Spot", "Futures"], horizontal=True,
                         label_visibility="collapsed")
    st.markdown("---")

    p_connect = st.button("Connect & Fetch", width="stretch", type="primary")


# ── Connection & Data Fetch ──────────────────────────────────────────────────

if "trades_df" not in st.session_state:
    st.session_state["trades_df"] = None
    st.session_state["exchange_name"] = None
    st.session_state["account_name"] = None
    st.session_state["current_balance"] = None

if p_connect:
    if not p_api_key or not p_api_secret:
        st.error("Please enter both API Key and API Secret.")
        st.stop()

    if not p_account_name:
        st.error("Please enter an account name.")
        st.stop()

    # Save account if in manual mode and save is checked
    if account_mode != "Saved Account":
        if p_save_account:
            save_account(p_account_name, exchange_id, p_api_key, p_api_secret)

    since_ms = int(pd.Timestamp(p_start_date, tz="UTC").timestamp() * 1000)

    with st.spinner(f"Fetching trades from {p_exchange}..."):
        try:
            trades_df = fetch_all_trades(exchange_id, p_api_key, p_api_secret, since_ms=since_ms)
        except Exception as e:
            st.error(f"Failed to fetch trades: {e}")
            st.stop()

    # Fetch current balance and snapshot it
    current_balance = None
    with st.spinner("Fetching current balance..."):
        try:
            bal_info = fetch_balance(exchange_id, p_api_key, p_api_secret)
            current_balance = bal_info["total_usdt"]
            save_balance_snapshot(p_account_name, current_balance)
        except Exception:
            pass

    # Filter by end date
    if not trades_df.empty:
        end_ts = pd.Timestamp(p_end_date, tz="UTC") + pd.Timedelta(days=1)
        trades_df = trades_df[trades_df["time"] < end_ts]

    st.session_state["trades_df"] = trades_df
    st.session_state["exchange_name"] = p_exchange
    st.session_state["account_name"] = p_account_name
    st.session_state["current_balance"] = current_balance

# Get current data
trades_df = st.session_state["trades_df"]
exchange_name = st.session_state["exchange_name"]
account_name = st.session_state["account_name"]
current_balance = st.session_state["current_balance"]

if trades_df is None:
    st.markdown(f"""
    <div class="hdr-banner">
        <div class="hdr-title">P/L Analytics</div>
        <div class="hdr-meta">
            Connect your exchange account to view trading statistics.<br>
            Enter your <span>read-only</span> API keys in the sidebar and click <span>Connect & Fetch</span>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Show saved accounts summary
    if saved_accounts:
        st.markdown('<hr class="noir">', unsafe_allow_html=True)
        st.markdown(f'{_section("Saved Accounts", C_PURPLE)}', unsafe_allow_html=True)
        for acct_name in saved_accounts:
            acct = get_account(acct_name)
            if acct:
                snapshots = load_balance_snapshots(acct_name)
                last_bal = f"${snapshots[-1]['balance_usdt']:,.2f}" if snapshots else "—"
                st.markdown(_stat_panel([
                    (acct_name, acct["exchange"].capitalize(), C_CYAN),
                    ("Last Balance", last_bal, C_TEXT),
                ]), unsafe_allow_html=True)
                st.markdown("")

    st.stop()

if trades_df.empty:
    st.warning("No trades found for the selected period.")
    st.stop()


# ── Filter by market type ────────────────────────────────────────────────────

filtered_df = trades_df
if p_market == "Spot":
    filtered_df = trades_df[trades_df["market_type"] == "spot"]
elif p_market == "Futures":
    filtered_df = trades_df[trades_df["market_type"] == "futures"]

if filtered_df.empty:
    st.warning(f"No {p_market.lower()} trades found for the selected period.")
    st.stop()


# ── Compute metrics ──────────────────────────────────────────────────────────

metrics = compute_metrics(filtered_df)
daily_pnl = compute_daily_pnl(filtered_df)
pnl_by_coin = compute_pnl_by_coin(filtered_df)


# ── Header Banner ────────────────────────────────────────────────────────────

_badge_cls = exchange_id
_market_label = p_market if p_market != "All" else "All Markets"
_acct_label = f" — {account_name}" if account_name else ""
_bal_label = f" &nbsp;&middot;&nbsp; balance <span>${current_balance:,.2f}</span>" if current_balance else ""

st.markdown(f"""
<div class="hdr-banner">
    <div class="hdr-title">
        {exchange_name}{_acct_label}
        <span class="hdr-badge {_badge_cls}">{_market_label}</span>
    </div>
    <div class="hdr-meta">
        <span>{metrics['n_trades']:,}</span> trades
        &nbsp;&middot;&nbsp; {p_start_date.isoformat()} to {p_end_date.isoformat()}
        &nbsp;&middot;&nbsp; volume <span>${metrics['total_volume']:,.2f}</span>
        {_bal_label}
    </div>
</div>
""", unsafe_allow_html=True)


# ── KPI Cards ────────────────────────────────────────────────────────────────

c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")
c1.markdown(_kpi("Total P&L",      f"${metrics['total_pnl']:+,.2f}",          _pnl_color(metrics['total_pnl'])),     unsafe_allow_html=True)
c2.markdown(_kpi("P&L %",          f"{metrics['pnl_pct']:+.2f}%",             _pnl_color(metrics['pnl_pct'])),       unsafe_allow_html=True)
c3.markdown(_kpi("Win Rate",       f"{metrics['win_rate']:.1f}%",             C_GREEN if metrics['win_rate'] >= 50 else C_RED), unsafe_allow_html=True)
c4.markdown(_kpi("Profit Factor",  f"{metrics['profit_factor']:.2f}",         C_GREEN if metrics['profit_factor'] >= 1 else C_RED), unsafe_allow_html=True)
c5.markdown(_kpi("Round Trips",    str(metrics['rt_count']),                  C_PURPLE),  unsafe_allow_html=True)
c6.markdown(_kpi("Total Trades",   f"{metrics['n_trades']:,}",               C_CYAN),    unsafe_allow_html=True)

st.markdown("")
d1, d2, d3, d4, d5, d6 = st.columns(6, gap="small")
d1.markdown(_kpi("Sharpe Ratio",   f"{metrics['sharpe_ratio']:.2f}",          C_CYAN),    unsafe_allow_html=True)
d2.markdown(_kpi("Sortino Ratio",  f"{metrics['sortino_ratio']:.2f}",         C_CYAN),    unsafe_allow_html=True)
d3.markdown(_kpi("Max Drawdown",   f"${metrics['max_drawdown']:,.2f}",        C_RED),     unsafe_allow_html=True)
d4.markdown(_kpi("Total Volume",   f"${metrics['total_volume']:,.0f}",        C_BLUE),    unsafe_allow_html=True)
d5.markdown(_kpi("Avg Trade Size", f"${metrics['avg_trade_size']:,.2f}",      C_MUTED),   unsafe_allow_html=True)
d6.markdown(_kpi("Total Fees",     f"${metrics['total_fees']:,.2f}",          C_AMBER),   unsafe_allow_html=True)

st.markdown("")
e1, e2, e3, e4 = st.columns(4, gap="small")
if current_balance is not None:
    # Estimate initial balance from trades
    bal_series = estimate_daily_balance(filtered_df, current_balance, p_end_date)
    initial_bal = float(bal_series.iloc[0]) if len(bal_series) > 0 else current_balance
    e1.markdown(_kpi("Initial Balance", f"${initial_bal:,.2f}",               C_MUTED),   unsafe_allow_html=True)
    e2.markdown(_kpi("Current Balance", f"${current_balance:,.2f}",           C_CYAN),    unsafe_allow_html=True)
else:
    e1.markdown(_kpi("Best Day",       f"${metrics['best_day_pnl']:+,.2f}",   C_GREEN),   unsafe_allow_html=True)
    e2.markdown(_kpi("Worst Day",      f"${metrics['worst_day_pnl']:+,.2f}",  C_RED),     unsafe_allow_html=True)
e3.markdown(_kpi("Coins Traded",   str(len(pnl_by_coin)),                     C_PURPLE),  unsafe_allow_html=True)
e4.markdown(_kpi("Best / Worst",   f"${metrics['best_day_pnl']:+,.0f} / ${metrics['worst_day_pnl']:+,.0f}", C_MUTED), unsafe_allow_html=True)


# ── Balance History ──────────────────────────────────────────────────────────

if current_balance is not None:
    st.markdown('<hr class="noir">', unsafe_allow_html=True)
    st.markdown(f'{_section("Balance History", C_CYAN)}', unsafe_allow_html=True)

    bal_series = estimate_daily_balance(filtered_df, current_balance, p_end_date)
    if len(bal_series) > 0:
        fig_bal = go.Figure()
        fig_bal.add_trace(go.Scatter(
            x=list(bal_series.index),
            y=list(bal_series.values),
            mode="lines", name="Estimated Balance",
            line=dict(color=C_CYAN, width=2),
            fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
        ))

        # Overlay real snapshots if available
        if account_name:
            snapshots = load_balance_snapshots(account_name)
            if len(snapshots) > 1:
                snap_times = [pd.Timestamp(s["time"]).date() for s in snapshots]
                snap_vals = [s["balance_usdt"] for s in snapshots]
                fig_bal.add_trace(go.Scatter(
                    x=snap_times, y=snap_vals,
                    mode="markers+lines", name="Snapshots",
                    line=dict(color=C_AMBER, width=1.5, dash="dot"),
                    marker=dict(color=C_AMBER, size=6),
                ))

        fig_bal.update_layout(**CHART_LAYOUT, height=300)
        fig_bal.update_yaxes(**GRID_STYLE)
        fig_bal.update_xaxes(**GRID_STYLE)
        st.plotly_chart(fig_bal, width="stretch")


# ── Equity Curve ─────────────────────────────────────────────────────────────

st.markdown('<hr class="noir">', unsafe_allow_html=True)
st.markdown(f'{_section("Cumulative P&L", C_PURPLE)}', unsafe_allow_html=True)

if len(daily_pnl) > 0:
    cum_pnl = daily_pnl.cumsum()
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        x=list(cum_pnl.index),
        y=list(cum_pnl.values),
        mode="lines", name="Cumulative P&L",
        line=dict(color=C_PURPLE, width=2),
        fill="tozeroy", fillcolor="rgba(168,85,247,0.06)",
    ))
    fig_eq.update_layout(**CHART_LAYOUT, height=350)
    fig_eq.update_yaxes(**GRID_STYLE)
    fig_eq.update_xaxes(**GRID_STYLE)
    st.plotly_chart(fig_eq, width="stretch")
else:
    st.info("Not enough data for equity curve.")


# ── P&L by Coin ─────────────────────────────────────────────────────────────

st.markdown('<hr class="noir">', unsafe_allow_html=True)
st.markdown(f'{_section("P&L by Coin", C_GREEN)}', unsafe_allow_html=True)

if pnl_by_coin:
    sorted_coins = sorted(pnl_by_coin.items(), key=lambda x: x[1], reverse=True)
    coin_names = [c[0] for c in sorted_coins]
    coin_pnls = [c[1] for c in sorted_coins]
    coin_colors = [C_GREEN if v >= 0 else C_RED for v in coin_pnls]

    fig_coins = go.Figure()
    fig_coins.add_trace(go.Bar(
        y=coin_names, x=coin_pnls,
        orientation="h", name="P&L",
        marker=dict(color=coin_colors),
    ))
    fig_coins.update_layout(**CHART_LAYOUT, height=max(200, len(coin_names) * 28 + 60))
    fig_coins.update_xaxes(**GRID_STYLE)
    fig_coins.update_yaxes(**GRID_STYLE, autorange="reversed")
    st.plotly_chart(fig_coins, width="stretch")
else:
    st.info("No completed round trips to show P&L by coin.")


# ── Calendar Heatmap ─────────────────────────────────────────────────────────

st.markdown('<hr class="noir">', unsafe_allow_html=True)
st.markdown(f'{_section("Daily P&L Heatmap", C_AMBER)}', unsafe_allow_html=True)

if len(daily_pnl) > 1:
    dates = pd.date_range(start=min(daily_pnl.index), end=max(daily_pnl.index), freq="D")
    full_daily = pd.Series(0.0, index=dates.date)
    for d, v in daily_pnl.items():
        full_daily[d] = v

    cal_data = []
    for d in full_daily.index:
        dt = pd.Timestamp(d)
        cal_data.append({
            "date": d,
            "weekday": dt.weekday(),
            "week": dt.isocalendar()[1] + (dt.year - pd.Timestamp(min(full_daily.index)).year) * 53,
            "pnl": full_daily[d],
        })
    cal_df = pd.DataFrame(cal_data)

    if not cal_df.empty:
        pivot = cal_df.pivot_table(index="weekday", columns="week", values="pnl", aggfunc="sum")
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        max_abs = max(abs(pivot.min().min()), abs(pivot.max().max()), 1)

        fig_cal = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=list(range(pivot.shape[1])),
            y=weekday_names[:pivot.shape[0]],
            colorscale=[
                [0.0, C_RED],
                [0.5, "#0c1018"],
                [1.0, C_GREEN],
            ],
            zmin=-max_abs, zmax=max_abs,
            showscale=True,
            colorbar=dict(
                title="P&L",
                tickfont=dict(size=9, color=C_MUTED),
                titlefont=dict(size=9, color=C_MUTED),
            ),
            hovertemplate="Week %{x}<br>%{y}<br>P&L: $%{z:,.2f}<extra></extra>",
        ))
        fig_cal.update_layout(**CHART_LAYOUT, height=220)
        fig_cal.update_xaxes(showticklabels=False)
        st.plotly_chart(fig_cal, width="stretch")
else:
    st.info("Not enough daily data for heatmap.")


# ── Analytics Tabs ───────────────────────────────────────────────────────────

st.markdown('<hr class="noir">', unsafe_allow_html=True)
st.markdown(f'{_section("Analytics", C_CYAN)}', unsafe_allow_html=True)

tab_log, tab_pairs, tab_breakdown = st.tabs(["Trade Log", "Most Traded Pairs", "Daily / Weekly"])

with tab_log:
    disp = filtered_df.tail(500).copy()
    disp["time"]     = pd.to_datetime(disp["time"]).dt.strftime("%Y-%m-%d %H:%M")
    disp["price"]    = disp["price"].map("${:,.4f}".format)
    disp["amount"]   = disp["amount"].map("{:.6f}".format)
    disp["cost"]     = disp["cost"].map("${:,.2f}".format)
    disp["fee"]      = disp["fee"].map("${:,.4f}".format)
    st.dataframe(
        disp[["time", "symbol", "side", "price", "amount", "cost", "fee", "market_type"]].rename(columns={
            "time": "Time", "symbol": "Symbol", "side": "Side", "price": "Price",
            "amount": "Amount", "cost": "USD Value", "fee": "Fee", "market_type": "Market",
        }),
        width="stretch", hide_index=True,
        height=min(36 * (len(disp) + 1) + 10, 560),
    )
    if len(filtered_df) > 500:
        st.caption(f"Showing last 500 of {len(filtered_df):,} total trades.")


with tab_pairs:
    most_traded = compute_most_traded(filtered_df)
    if not most_traded.empty:
        mt_disp = most_traded.copy()
        mt_disp["volume"] = mt_disp["volume"].map("${:,.2f}".format)
        mt_disp["trades"] = mt_disp["trades"].map(str)
        mt_disp["pnl"] = most_traded["symbol"].map(
            lambda s: f"${pnl_by_coin.get(s, 0.0):+,.2f}"
        )
        st.dataframe(
            mt_disp.rename(columns={
                "symbol": "Symbol", "volume": "Volume", "trades": "Trades", "pnl": "P&L",
            }),
            width="stretch", hide_index=True,
        )
    else:
        st.info("No trade data available.")


with tab_breakdown:
    col_daily, col_weekly = st.columns(2, gap="medium")

    with col_daily:
        st.markdown(f'<div style="font-size:0.75rem;color:{C_CYAN};font-weight:500;'
                    f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">'
                    f'Daily P&L</div>', unsafe_allow_html=True)
        if len(daily_pnl) > 0:
            daily_disp = pd.DataFrame({
                "Date": [str(d) for d in daily_pnl.index],
                "P&L": [f"${v:+,.2f}" for v in daily_pnl.values],
            })
            # Add balance column if available
            if current_balance is not None:
                bal_series = estimate_daily_balance(filtered_df, current_balance, p_end_date)
                bal_map = {str(d): f"${v:,.2f}" for d, v in bal_series.items()}
                daily_disp["Balance"] = daily_disp["Date"].map(lambda d: bal_map.get(d, "—"))
            st.dataframe(daily_disp, width="stretch", hide_index=True,
                         height=min(36 * (len(daily_disp) + 1) + 10, 400))
        else:
            st.info("No daily P&L data.")

    with col_weekly:
        st.markdown(f'<div style="font-size:0.75rem;color:{C_PURPLE};font-weight:500;'
                    f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">'
                    f'Weekly Summary</div>', unsafe_allow_html=True)
        weekly = compute_weekly_breakdown(filtered_df)
        if not weekly.empty:
            w_disp = weekly.copy()
            w_disp["volume"] = w_disp["volume"].map("${:,.2f}".format)
            w_disp["trades"] = w_disp["trades"].map(str)
            st.dataframe(
                w_disp.rename(columns={
                    "year": "Year", "week": "Week", "volume": "Volume", "trades": "Trades",
                }),
                width="stretch", hide_index=True,
                height=min(36 * (len(w_disp) + 1) + 10, 400))
        else:
            st.info("No weekly data.")


# ── Footer ───────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="footer">P/L // ANALYTICS &middot; '
    'Binance & Bybit via CCXT &middot; '
    'Read-only API access &middot; Not financial advice</div>',
    unsafe_allow_html=True,
)
