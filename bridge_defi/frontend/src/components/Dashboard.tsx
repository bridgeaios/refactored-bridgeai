interface DashboardProps {
  isConnected: boolean
}

export default function Dashboard({ isConnected }: DashboardProps) {
  return (
    <div className="dashboard">
      <div className="card">
        <h2>Portfolio Overview</h2>
        <div className="grid">
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">Total Value</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">Available Balance</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">Staked</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              <span className="tier-badge tier-basic">Basic</span>
            </div>
            <div className="stat-label">Your Tier</div>
          </div>
        </div>
      </div>
      <div className="card">
        <h2>Risk Score</h2>
        <div className="stat">
          <div className="stat-value volatility-low">0/100</div>
          <div className="stat-label">Low Risk</div>
        </div>
      </div>
      {!isConnected && (
        <div className="card">
          <p>Connect your wallet to access DeFi features</p>
        </div>
      )}
    </div>
  )
}
