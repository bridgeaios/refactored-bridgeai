import { useState } from 'react'
import { useWallet } from '../../hooks/useWallet'

export function LendingPage() {
  const { isConnected } = useWallet()
  const [amount, setAmount] = useState('')
  const [collateralRatio, setCollateralRatio] = useState('130')

  const handleBorrow = async () => {
    if (!isConnected) return
    console.log('Borrow:', amount, 'Collateral ratio:', collateralRatio)
  }

  const handleRepay = async () => {
    if (!isConnected) return
    console.log('Repay:', amount)
  }

  const handleLiquidate = async () => {
    if (!isConnected) return
    console.log('Liquidate position')
  }

  return (
    <div className="lending">
      <div className="card">
        <h1>Lending</h1>
        <h2>Borrow Assets</h2>
        <div className="form-group">
          <label>Amount (USDC)</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
          />
        </div>
        <div className="form-group">
          <label>Collateral Ratio: {collateralRatio}%</label>
          <input
            type="range"
            min="110"
            max="150"
            value={collateralRatio}
            onChange={(e) => setCollateralRatio(e.target.value)}
          />
          <small>Min: 110%, Max: 150%</small>
        </div>
        <button className="btn" onClick={handleBorrow} disabled={!isConnected}>
          Borrow
        </button>
      </div>

      <div className="card">
        <h2>Your Loans</h2>
        <div className="stat">
          <div className="stat-value">$0.00</div>
          <div className="stat-label">Total Borrowed</div>
        </div>
        <div className="stat">
          <div className="stat-value">$0.00</div>
          <div className="stat-label">Collateral Value</div>
        </div>
        <button className="btn" onClick={handleRepay} disabled={!isConnected}>
          Repay
        </button>
        <button className="btn" onClick={handleLiquidate} disabled={!isConnected}>
          Liquidate (5% bonus)
        </button>
      </div>
    </div>
  )
}
