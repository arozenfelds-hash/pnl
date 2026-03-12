import './KpiCard.css'

export default function KpiCard({ label, value, color = 'var(--cyan)' }) {
  return (
    <div className="kpi" style={{ '--accent': color }}>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  )
}
