import { useState } from 'react'
import { useWallet } from '../../hooks/useWallet'

export function StakingPage() {
  const { isConnected } = useWallet()
  const [amount, setAmount] = useState('')
  const [lockPeriod, setLockPeriod] = useState('30')

  const handleStake = async () => {
    if (!isConnected) return
    console.log('Stake:', amount, 'Days:', lockPeriod)
  }

  const handleUnstake = async () => {
    if (!isConnected) return
    console.log('Request unstake')
  }

  const apyRates: Record<string, string> = {
    '30': '5%',
    '60': '8%',
    '90': '12%',
    '180': '18%',
  }

  return (
    <div className="staking">
      <div className="card">
        <h1>Staking</h1>
        <h2>Stake BRDG Tokens</h2>
        <div className="form-group">
          <label>Amount (BRDG)</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
          />
        </div>
        <div className="form-group">
          <label>Lock Period</label>
          <select value={lockPeriod} onChange={(e) => setLockPeriod(e.target.value)}>
            <option value="30">30 days - {apyRates['30']} APY</option>
            <option value="60">60 days - {apyRates['60']} APY</option>
            <option value="90">90 days - {apyRates['90']} APY</option>
            <option value="180">180 days - {apyRates['180']} APY</option>
          </select>
        </div>
        <button className="btn" onClick={handleStake} disabled={!isConnected}>
          Stake
        </button>
      </div>

      <div className="card">
        <h2>Your Stakes</h2>
        <div className="grid">
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">Total Staked</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">Pending Rewards</div>
          </div>
          <div className="stat">
            <div className="stat-value">0</div>
            <div className="stat-label">Active Stakes</div>
          </div>
        </div>
        <button className="btn" onClick={handleUnstake} disabled={!isConnected}>
          Request Unstake
        </button>
      </div>
    </div>
  )
}
