export function CfoPage() {
  return (
    <div className="cfo">
      <div className="card">
        <h1>CFO Dashboard</h1>
        <div className="grid">
          <div className="stat">
            <div className="stat-value">Closed</div>
            <div className="stat-label">Circuit Breaker</div>
          </div>
          <div className="stat">
            <div className="stat-value">40 / 30 / 20 / 10</div>
            <div className="stat-label">Economic Weights</div>
          </div>
        </div>
      </div>
    </div>
  )
}
