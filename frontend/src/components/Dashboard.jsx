import { useState, useMemo } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell, ReferenceLine,
} from 'recharts'
import KpiCard from './KpiCard'
import DataTable from './DataTable'
import './Dashboard.css'

const fmt = (v, d = 2) => v != null ? `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })}` : '\u2014'
const fmtSigned = (v, d = 2) => v != null ? `${v >= 0 ? '+' : ''}${fmt(v, d).replace('$', '$')}` : '\u2014'
const pnlColor = v => v >= 0 ? 'var(--green)' : 'var(--red)'

function useThemeColors() {
  const s = getComputedStyle(document.documentElement)
  return {
    cyan: s.getPropertyValue('--cyan').trim(),
    purple: s.getPropertyValue('--purple').trim(),
    green: s.getPropertyValue('--green').trim(),
    red: s.getPropertyValue('--red').trim(),
    muted: s.getPropertyValue('--muted').trim(),
    border: s.getPropertyValue('--border').trim(),
    text: s.getPropertyValue('--text').trim(),
  }
}

function SectionHeader({ title, color = 'var(--cyan)' }) {
  return (
    <div className="sec-header">
      <span className="sec-dot" style={{ background: color }} />
      {title}
      <span className="sec-line" />
    </div>
  )
}

function ChartTooltip({ active, payload, label, prefix = '$' }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="tooltip-label">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="tooltip-val" style={{ color: p.color }}>
          {p.name}: {prefix}{Number(p.value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
        </div>
      ))}
    </div>
  )
}

export default function Dashboard({ data, info }) {
  const [activeTab, setActiveTab] = useState('log')
  const tc = useThemeColors()
  const m = data.metrics
  const bal = data.balance

  // Cumulative PnL for chart
  const cumPnl = []
  let cumSum = 0
  for (const d of data.daily_pnl) {
    cumSum += d.pnl
    cumPnl.push({ date: d.date, pnl: cumSum })
  }

  const marketLabel = info?.market === 'all' ? 'All Markets' : info?.market?.charAt(0).toUpperCase() + info?.market?.slice(1)

  return (
    <div className="dashboard">
      {/* Header Banner */}
      <div className="header-banner">
        <div className="header-top">
          <h1 className="header-title">
            {info?.exchange}
            {info?.account && <span className="header-account"> {'\u2014'} {info.account}</span>}
          </h1>
          <span className={`header-badge ${info?.exchange?.toLowerCase()}`}>{marketLabel}</span>
        </div>
        <div className="header-meta">
          <span className="hl">{m.n_trades?.toLocaleString()}</span> trades
          {' \u00b7 '}{info?.start} to {info?.end}
          {' \u00b7 '}volume <span className="hl">{fmt(m.total_volume, 0)}</span>
          {' \u00b7 '}turnover <span className="hl">{fmt(m.turnover, 0)}</span>
          {bal.total ? <>{' \u00b7 '}balance <span className="hl">{fmt(bal.total)}</span></> : null}
        </div>
      </div>

      {/* KPI Row 1 */}
      <div className="kpi-grid six">
        <KpiCard label="Total P&L" value={fmtSigned(m.total_pnl)} color={pnlColor(m.total_pnl)} />
        <KpiCard label="P&L %" value={`${m.pnl_pct >= 0 ? '+' : ''}${m.pnl_pct?.toFixed(2)}%`} color={pnlColor(m.pnl_pct)} />
        <KpiCard label="Win Rate" value={`${m.win_rate?.toFixed(1)}%`} color={m.win_rate >= 50 ? 'var(--green)' : 'var(--red)'} />
        <KpiCard label="Profit Factor" value={m.profit_factor?.toFixed(2)} color={m.profit_factor >= 1 ? 'var(--green)' : 'var(--red)'} />
        <KpiCard label="Round Trips" value={m.rt_count} color="var(--purple)" />
        <KpiCard label="Total Trades" value={m.n_trades?.toLocaleString()} color="var(--cyan)" />
      </div>

      {/* KPI Row 2 */}
      <div className="kpi-grid six">
        <KpiCard label="Sharpe Ratio" value={m.sharpe_ratio?.toFixed(2)} color="var(--cyan)" />
        <KpiCard label="Sortino Ratio" value={m.sortino_ratio?.toFixed(2)} color="var(--cyan)" />
        <KpiCard label="Max Drawdown" value={fmt(m.max_drawdown)} color="var(--red)" />
        <KpiCard label="Total Volume" value={fmt(m.total_volume, 0)} color="var(--blue)" />
        <KpiCard label="Turnover" value={fmt(m.turnover, 0)} color="var(--blue)" />
        <KpiCard label="Avg Trade Size" value={fmt(m.avg_trade_size)} color="var(--muted)" />
        <KpiCard label="Total Fees" value={fmt(m.total_fees)} color="var(--amber)" />
      </div>

      {/* KPI Row 3: Balance */}
      {bal.total > 0 && (
        <div className="kpi-grid six">
          <KpiCard label="Initial Balance" value={data.initial_balance != null ? fmt(data.initial_balance) : '\u2014'} color="var(--muted)" />
          <KpiCard label="Total Balance" value={fmt(bal.total)} color="var(--cyan)" />
          <KpiCard label={bal.label_a} value={fmt(bal.account_a)} color="var(--amber)" />
          <KpiCard label={bal.label_b} value={fmt(bal.account_b)} color="var(--purple)" />
          <KpiCard label="Coins Traded" value={data.coins_traded} color="var(--purple)" />
          <KpiCard label="Best / Worst" value={`${fmt(m.best_day_pnl, 0)} / ${fmt(m.worst_day_pnl, 0)}`} color="var(--muted)" />
        </div>
      )}

      {/* Current Holdings */}
      {data.holdings?.length > 0 && (
        <section>
          <SectionHeader title="Current Holdings" color="var(--amber)" />
          <DataTable
            columns={[
              { key: 'asset', label: 'Asset' },
              { key: 'amount', label: 'Amount', render: v => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 8 }) },
              { key: 'account', label: 'Account' },
            ]}
            data={data.holdings}
          />
        </section>
      )}

      {/* Open Positions */}
      {data.positions?.length > 0 && (
        <section>
          <SectionHeader title="Open Positions" color="var(--purple)" />
          <div className="kpi-grid two" style={{ marginBottom: 12 }}>
            <KpiCard
              label="Total Unrealized P&L"
              value={fmtSigned(data.positions.reduce((s, p) => s + p.unrealized_pnl, 0))}
              color={pnlColor(data.positions.reduce((s, p) => s + p.unrealized_pnl, 0))}
            />
            <KpiCard
              label="Total Notional"
              value={fmt(data.positions.reduce((s, p) => s + p.notional, 0))}
              color="var(--cyan)"
            />
          </div>
          <DataTable
            columns={[
              { key: 'symbol', label: 'Symbol' },
              { key: 'side', label: 'Side', style: (v) => ({ color: v === 'long' ? 'var(--green)' : 'var(--red)' }) },
              { key: 'size', label: 'Size', render: v => Number(v).toFixed(4) },
              { key: 'entry_price', label: 'Entry', render: v => fmt(v, 4) },
              { key: 'mark_price', label: 'Mark', render: v => fmt(v, 4) },
              { key: 'notional', label: 'Notional', render: v => fmt(v) },
              { key: 'unrealized_pnl', label: 'Unreal. P&L', render: v => fmtSigned(v), style: v => ({ color: pnlColor(v) }) },
              { key: 'leverage', label: 'Lev' },
              { key: 'margin_mode', label: 'Margin' },
            ]}
            data={data.positions}
          />
        </section>
      )}

      {/* Deposits & Withdrawals */}
      {data.transfers?.length > 0 && (
        <section>
          <SectionHeader title="Deposits & Withdrawals" color="var(--amber)" />
          <div className="kpi-grid three" style={{ marginBottom: 12 }}>
            <KpiCard
              label="Total Deposited"
              value={fmt(data.transfers.filter(t => t.type === 'deposit').reduce((s, t) => s + t.amount, 0))}
              color="var(--green)"
            />
            <KpiCard
              label="Total Withdrawn"
              value={fmt(data.transfers.filter(t => t.type === 'withdrawal').reduce((s, t) => s + t.amount, 0))}
              color="var(--red)"
            />
            <KpiCard
              label="Net Transfers"
              value={fmtSigned(
                data.transfers.filter(t => t.type === 'deposit').reduce((s, t) => s + t.amount, 0) -
                data.transfers.filter(t => t.type === 'withdrawal').reduce((s, t) => s + t.amount, 0)
              )}
              color={pnlColor(
                data.transfers.filter(t => t.type === 'deposit').reduce((s, t) => s + t.amount, 0) -
                data.transfers.filter(t => t.type === 'withdrawal').reduce((s, t) => s + t.amount, 0)
              )}
            />
          </div>
          <DataTable
            columns={[
              { key: 'time', label: 'Time' },
              { key: 'type', label: 'Type', style: v => ({ color: v === 'deposit' ? 'var(--green)' : 'var(--red)' }) },
              { key: 'currency', label: 'Currency' },
              { key: 'amount', label: 'Amount', render: v => Number(v).toLocaleString(undefined, { maximumFractionDigits: 4 }) },
              { key: 'status', label: 'Status' },
            ]}
            data={data.transfers}
            maxHeight={350}
          />
        </section>
      )}

      {/* Balance History */}
      {data.balance_history?.length > 0 && (
        <section>
          <SectionHeader title="Balance History" color="var(--cyan)" />
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={data.balance_history}>
                <defs>
                  <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={tc.cyan} stopOpacity={0.15} />
                    <stop offset="100%" stopColor={tc.cyan} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={tc.border} />
                <XAxis dataKey="date" tick={{ fill: tc.muted, fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: tc.muted, fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `$${(v/1000).toFixed(1)}k`} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="balance" stroke={tc.cyan} strokeWidth={2} fill="url(#balGrad)" name="Balance" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* Cumulative P&L */}
      {cumPnl.length > 0 && (
        <section>
          <SectionHeader title="Cumulative P&L" color="var(--purple)" />
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={cumPnl}>
                <defs>
                  <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={tc.purple} stopOpacity={0.15} />
                    <stop offset="100%" stopColor={tc.purple} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={tc.border} />
                <XAxis dataKey="date" tick={{ fill: tc.muted, fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: tc.muted, fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `$${v.toFixed(0)}`} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="pnl" stroke={tc.purple} strokeWidth={2} fill="url(#pnlGrad)" name="Cumulative P&L" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* P&L by Coin */}
      {data.pnl_by_coin?.length > 0 && (() => {
        const maxAbs = Math.max(...data.pnl_by_coin.map(d => Math.abs(d.pnl)));
        return (
          <section>
            <SectionHeader title="P&L by Coin" color="var(--green)" />
            <div className="chart-container" style={{ padding: '16px' }}>
              {data.pnl_by_coin.map((entry, i) => {
                const pct = maxAbs > 0 ? (Math.abs(entry.pnl) / maxAbs) * 45 : 0;
                const isPositive = entry.pnl >= 0;
                const color = isPositive ? tc.green : tc.red;
                return (
                  <div key={i} className="coin-bar-row">
                    <span className="coin-bar-label">{entry.symbol}</span>
                    <div className="coin-bar-track">
                      <div className="coin-bar-zero" />
                      <div
                        className={`coin-bar-fill ${isPositive ? 'positive' : 'negative'}`}
                        style={{
                          width: `${pct}%`,
                          background: color,
                          [isPositive ? 'left' : 'right']: '50%',
                        }}
                      />
                    </div>
                    <span className="coin-bar-value" style={{ color }}>
                      {entry.pnl >= 0 ? '+' : ''}{fmt(entry.pnl)}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })()}

      {/* Daily P&L Heatmap (bar chart version) */}
      {data.daily_pnl?.length > 1 && (
        <section>
          <SectionHeader title="Daily P&L" color="var(--amber)" />
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.daily_pnl}>
                <CartesianGrid strokeDasharray="3 3" stroke={tc.border} />
                <XAxis dataKey="date" tick={{ fill: tc.muted, fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: tc.muted, fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `$${v.toFixed(0)}`} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="pnl" name="P&L" radius={[2, 2, 0, 0]}>
                  {data.daily_pnl.map((entry, i) => (
                    <Cell key={i} fill={entry.pnl >= 0 ? tc.green : tc.red} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* Analytics Tabs */}
      <section>
        <SectionHeader title="Analytics" color="var(--cyan)" />
        <div className="tabs">
          <button className={activeTab === 'log' ? 'active' : ''} onClick={() => setActiveTab('log')}>Trade Log</button>
          <button className={activeTab === 'orders' ? 'active' : ''} onClick={() => setActiveTab('orders')}>Open Orders{data.open_orders?.length ? ` (${data.open_orders.length})` : ''}</button>
          <button className={activeTab === 'pairs' ? 'active' : ''} onClick={() => setActiveTab('pairs')}>Most Traded</button>
          <button className={activeTab === 'weekly' ? 'active' : ''} onClick={() => setActiveTab('weekly')}>Weekly</button>
        </div>

        {activeTab === 'log' && (
          <>
            <DataTable
              columns={[
                { key: 'time', label: 'Time' },
                { key: 'symbol', label: 'Symbol' },
                { key: 'action', label: 'Action', style: (v) => ({
                  color: v === 'Open Long' || v === 'buy' ? 'var(--green)'
                       : v === 'Open Short' || v === 'sell' ? 'var(--red)'
                       : v === 'Close Short' ? 'var(--green)'
                       : v === 'Close Long' ? 'var(--red)'
                       : 'var(--text)'
                }) },
                { key: 'price', label: 'Price', render: v => fmt(v, 4) },
                { key: 'amount', label: 'Amount', render: v => Number(v).toFixed(6) },
                { key: 'cost', label: 'USD Value', render: v => fmt(v) },
                { key: 'fee', label: 'Fee', render: v => fmt(v, 4) },
                { key: 'market_type', label: 'Market' },
              ]}
              data={data.trade_log}
              maxHeight={520}
            />
            {data.total_trades > 500 && (
              <p className="table-note">Showing last 500 of {data.total_trades.toLocaleString()} total trades.</p>
            )}
          </>
        )}

        {activeTab === 'orders' && (
          data.open_orders?.length > 0 ? (
            <DataTable
              columns={[
                { key: 'time', label: 'Time' },
                { key: 'symbol', label: 'Symbol' },
                { key: 'type', label: 'Type' },
                { key: 'side', label: 'Side', style: v => ({ color: v === 'buy' ? 'var(--green)' : 'var(--red)' }) },
                { key: 'price', label: 'Price', render: v => fmt(v, 4) },
                { key: 'amount', label: 'Amount', render: v => Number(v).toFixed(6) },
                { key: 'cost', label: 'Value', render: v => fmt(v) },
                { key: 'filled', label: 'Filled', render: v => Number(v).toFixed(6) },
                { key: 'remaining', label: 'Remaining', render: v => Number(v).toFixed(6) },
                { key: 'market_type', label: 'Market' },
              ]}
              data={data.open_orders}
              maxHeight={520}
            />
          ) : (
            <p className="table-note">No open orders.</p>
          )
        )}

        {activeTab === 'pairs' && (
          <DataTable
            columns={[
              { key: 'symbol', label: 'Symbol' },
              { key: 'volume', label: 'Volume', render: v => fmt(v) },
              { key: 'trades', label: 'Trades' },
              { key: 'pnl', label: 'P&L', render: v => fmtSigned(v), style: v => ({ color: pnlColor(v) }) },
            ]}
            data={data.most_traded}
          />
        )}

        {activeTab === 'weekly' && (
          <DataTable
            columns={[
              { key: 'year', label: 'Year' },
              { key: 'week', label: 'Week' },
              { key: 'volume', label: 'Volume', render: v => fmt(v) },
              { key: 'trades', label: 'Trades' },
            ]}
            data={data.weekly}
          />
        )}
      </section>

      {/* Footer */}
      <footer className="dashboard-footer">
        P/L // ANALYTICS &middot; Binance & Bybit via CCXT &middot; Read-only API access &middot; Not financial advice
      </footer>
    </div>
  )
}
