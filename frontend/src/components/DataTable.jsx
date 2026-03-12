import './DataTable.css'

export default function DataTable({ columns, data, maxHeight = 500 }) {
  if (!data || data.length === 0) {
    return <div className="table-empty">No data available.</div>
  }

  return (
    <div className="table-wrap" style={{ maxHeight }}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              {columns.map(col => {
                const val = col.render ? col.render(row[col.key], row) : row[col.key]
                return <td key={col.key} style={col.style?.(row[col.key], row)}>{val}</td>
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
