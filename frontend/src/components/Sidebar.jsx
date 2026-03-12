import { useState } from 'react'
import './Sidebar.css'

function daysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().split('T')[0]
}

export default function Sidebar({ accounts, onConnect, onDeleteAccount, loading, theme, onThemeChange }) {
  const [mode, setMode] = useState(accounts.length > 0 ? 'saved' : 'manual')
  const [selectedAccount, setSelectedAccount] = useState('')
  const [exchange, setExchange] = useState('binance')
  const [accountName, setAccountName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [startDate, setStartDate] = useState(daysAgo(90))
  const [endDate, setEndDate] = useState(daysAgo(0))
  const [market, setMarket] = useState('all')
  const [saveAcct, setSaveAcct] = useState(true)

  function handleSubmit(e) {
    e.preventDefault()
    let name, exch, key, secret
    if (mode === 'saved' && selectedAccount) {
      const acct = accounts.find(a => a.name === selectedAccount)
      if (!acct) return
      name = acct.name
      exch = acct.exchange
      // For saved accounts, keys come from server
      key = '__saved__'
      secret = '__saved__'
    } else {
      name = accountName
      exch = exchange
      key = apiKey
      secret = apiSecret
    }
    if (!name) return
    onConnect({
      account_name: name,
      exchange: exch,
      api_key: key,
      api_secret: secret,
      start_date: startDate,
      end_date: endDate,
      market_filter: market,
      save_account: mode !== 'saved' && saveAcct,
    })
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="logo-text">P/L // Analytics</h1>
        <p className="logo-sub">Binance & Bybit Account Statistics</p>
      </div>

      <div className="sidebar-divider" />

      <form onSubmit={handleSubmit}>
        <div className="section-label">Account</div>
        <div className="toggle-group">
          <button type="button" className={mode === 'saved' ? 'active' : ''} onClick={() => setMode('saved')}>Saved</button>
          <button type="button" className={mode === 'manual' ? 'active' : ''} onClick={() => setMode('manual')}>Manual</button>
        </div>

        {mode === 'saved' ? (
          accounts.length > 0 ? (
            <div className="field-group">
              <select value={selectedAccount} onChange={e => setSelectedAccount(e.target.value)}>
                <option value="">Select account...</option>
                {accounts.map(a => (
                  <option key={a.name} value={a.name}>{a.name} ({a.exchange})</option>
                ))}
              </select>
              {selectedAccount && (
                <button type="button" className="btn-delete" onClick={() => onDeleteAccount(selectedAccount)}>
                  Delete Account
                </button>
              )}
            </div>
          ) : (
            <p className="hint">No saved accounts yet.</p>
          )
        ) : (
          <>
            <div className="section-label">Exchange</div>
            <div className="toggle-group">
              <button type="button" className={exchange === 'binance' ? 'active' : ''} onClick={() => setExchange('binance')}>Binance</button>
              <button type="button" className={exchange === 'bybit' ? 'active' : ''} onClick={() => setExchange('bybit')}>Bybit</button>
            </div>

            <div className="section-label">API Keys</div>
            <div className="field-group">
              <input placeholder="Account Name" value={accountName} onChange={e => setAccountName(e.target.value)} />
              <input placeholder="API Key" type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} />
              <input placeholder="API Secret" type="password" value={apiSecret} onChange={e => setApiSecret(e.target.value)} />
              <label className="checkbox-row">
                <input type="checkbox" checked={saveAcct} onChange={e => setSaveAcct(e.target.checked)} />
                <span>Save account</span>
              </label>
            </div>
          </>
        )}

        <div className="sidebar-divider" />

        <div className="section-label">Period</div>
        <div className="field-group">
          <label className="field-label">Start</label>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
          <label className="field-label">End</label>
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
        </div>

        <div className="sidebar-divider" />

        <div className="section-label">Market</div>
        <div className="toggle-group tri">
          {['all', 'spot', 'futures'].map(m => (
            <button key={m} type="button" className={market === m ? 'active' : ''} onClick={() => setMarket(m)}>
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>

        <div className="sidebar-divider" />

        <button type="submit" className="btn-connect" disabled={loading}>
          {loading ? 'Connecting...' : 'Connect & Fetch'}
        </button>
      </form>

      <div className="sidebar-spacer" />
      <div className="sidebar-divider" />
      <div className="section-label">Theme</div>
      <div className="toggle-group">
        <button type="button" className={theme === 'dark' ? 'active' : ''} onClick={() => onThemeChange('dark')}>Dark</button>
        <button type="button" className={theme === 'light' ? 'active' : ''} onClick={() => onThemeChange('light')}>Light</button>
      </div>
    </aside>
  )
}
