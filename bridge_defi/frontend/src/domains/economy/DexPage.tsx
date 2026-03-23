import { useState } from 'react'
import { useWallet } from '../../hooks/useWallet'

export function DexPage() {
  const { isConnected } = useWallet()
  const [fromToken, setFromToken] = useState('ETH')
  const [toToken, setToToken] = useState('USDC')
  const [amount, setAmount] = useState('')
  const [slippage, setSlippage] = useState('0.5')

  const tokens = ['ETH', 'USDC', 'USDT', 'BRDG', 'SOL', 'WBTC']

  const handleSwap = async () => {
    if (!isConnected) return
    console.log('Swap:', amount, fromToken, '->', toToken, 'Slippage:', slippage)
  }

  return (
    <div className="dex">
      <div className="card">
        <h1>DEX</h1>
        <h2>Swap Tokens</h2>
        <div className="form-group">
          <label>From</label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select value={fromToken} onChange={(e) => setFromToken(e.target.value)}>
              {tokens.map((token) => (
                <option key={token} value={token}>
                  {token}
                </option>
              ))}
            </select>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              style={{ flex: 1 }}
            />
          </div>
        </div>
        <div className="form-group">
          <label>To</label>
          <select value={toToken} onChange={(e) => setToToken(e.target.value)}>
            {tokens.map((token) => (
              <option key={token} value={token}>
                {token}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Max Slippage: {slippage}%</label>
          <input
            type="range"
            min="0.1"
            max="5"
            step="0.1"
            value={slippage}
            onChange={(e) => setSlippage(e.target.value)}
          />
        </div>
        <button className="btn" onClick={handleSwap} disabled={!isConnected}>
          Swap
        </button>
      </div>

      <div className="card">
        <h2>Exchange Rates</h2>
        <div className="grid">
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">ETH to USDC</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">BRDG to USDC</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">SOL to ETH</div>
          </div>
        </div>
      </div>
    </div>
  )
}
