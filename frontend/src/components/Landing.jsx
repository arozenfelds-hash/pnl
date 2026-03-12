import './Landing.css'

export default function Landing({ accounts }) {
  return (
    <div className="landing">
      <div className="landing-banner">
        <div className="banner-glow" />
        <h1 className="landing-title">P/L Analytics</h1>
        <p className="landing-desc">
          Connect your exchange account to view trading statistics.<br />
          Enter your <em>read-only</em> API keys in the sidebar and click <em>Connect & Fetch</em>.
        </p>
      </div>

      {accounts.length > 0 && (
        <div className="saved-accounts">
          <div className="section-header">
            <span className="dot" style={{ background: 'var(--purple)' }} />
            Saved Accounts
          </div>
          {accounts.map(a => (
            <div key={a.name} className="account-card">
              <div className="account-row">
                <span className="account-name">{a.name}</span>
                <span className="account-exchange">{a.exchange}</span>
              </div>
              <div className="account-row">
                <span className="account-label">Last Balance</span>
                <span className="account-value">
                  {a.last_balance != null ? `$${a.last_balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '\u2014'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
