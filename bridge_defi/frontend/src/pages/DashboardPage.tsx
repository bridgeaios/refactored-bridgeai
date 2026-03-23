interface DashboardPageProps {
  isConnected?: boolean
  address?: string | null
}

export function DashboardPage({ isConnected, address }: DashboardPageProps) {
  return (
    <section className="page dashboard-page">
      <div className="card">
        <h1>Dashboard</h1>
        <p>Central operational view for Phase 4.</p>
        <div className="grid" style={{ marginTop: '1rem' }}>
          <div className="stat">
            <div className="stat-value">{isConnected ? 'Connected' : 'Offline'}</div>
            <div className="stat-label">Wallet</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : '-'}
            </div>
            <div className="stat-label">Address</div>
          </div>
          <div className="stat">
            <div className="stat-value">Phase 4</div>
            <div className="stat-label">UI Target</div>
          </div>
        </div>
      </div>
    </section>
  )
}
