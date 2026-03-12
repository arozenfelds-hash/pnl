import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import Landing from './components/Landing'
import './App.css'

const API = window.location.port === '5173'
  ? 'http://localhost:8505'
  : ''

export default function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [connectionInfo, setConnectionInfo] = useState(null)
  const [theme, setTheme] = useState(() => localStorage.getItem('pnl-theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('pnl-theme', theme)
  }, [theme])

  async function fetchAccounts() {
    try {
      const res = await fetch(`${API}/api/accounts`)
      const json = await res.json()
      setAccounts(json.accounts || [])
    } catch { /* ignore */ }
  }

  async function handleConnect(params) {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Connection failed')
      }
      const json = await res.json()
      setData(json)
      setConnectionInfo({
        exchange: params.exchange,
        account: params.account_name,
        start: params.start_date,
        end: params.end_date,
        market: params.market_filter,
      })
      fetchAccounts()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteAccount(name) {
    try {
      await fetch(`${API}/api/accounts/${encodeURIComponent(name)}`, { method: 'DELETE' })
      fetchAccounts()
    } catch { /* ignore */ }
  }

  useEffect(() => { fetchAccounts() }, [])

  return (
    <div className="app">
      <Sidebar
        accounts={accounts}
        onConnect={handleConnect}
        onDeleteAccount={handleDeleteAccount}
        loading={loading}
        theme={theme}
        onThemeChange={setTheme}
      />
      <main className="main-content">
        {error && <div className="error-banner">{error}</div>}
        {loading && <div className="loading-overlay"><div className="loader" /><span>Fetching data...</span></div>}
        {data ? <Dashboard data={data} info={connectionInfo} /> : <Landing accounts={accounts} />}
      </main>
    </div>
  )
}
