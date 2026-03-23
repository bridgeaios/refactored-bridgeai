import { useWallet } from '../../hooks/useWallet'

export function TreasuryPage() {
  const { isConnected, address } = useWallet()

  return (
    <div className="treasury">
      <div className="card">
        <h1>Treasury</h1>
        <p>{isConnected ? `Connected: ${address ?? 'wallet'}` : 'Wallet not connected'}</p>
        <div className="grid">
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">Total Treasury</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">UBI Pool (40%)</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">Operations (20%)</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">Founder (10%)</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Revenue Distribution</h2>
        <div className="grid">
          <div className="stat">
            <div className="stat-value">40%</div>
            <div className="stat-label">UBI</div>
          </div>
          <div className="stat">
            <div className="stat-value">30%</div>
            <div className="stat-label">Treasury</div>
          </div>
          <div className="stat">
            <div className="stat-value">20%</div>
            <div className="stat-label">Operations</div>
          </div>
          <div className="stat">
            <div className="stat-value">10%</div>
            <div className="stat-label">Founder</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Payment Methods</h2>
        <div className="grid">
          <div className="stat">
            <div className="stat-value">ZAR/NGN</div>
            <div className="stat-label">Paystack</div>
          </div>
          <div className="stat">
            <div className="stat-value">Global</div>
            <div className="stat-label">PayPal</div>
          </div>
          <div className="stat">
            <div className="stat-value">ETH/SOL</div>
            <div className="stat-label">Crypto</div>
          </div>
        </div>
      </div>
    </div>
  )
}
