import { useState } from 'react'

interface DexProps {
  isConnected: boolean
}

export default function Dex({ isConnected }: DexProps) {
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
        <h2>Swap Tokens</h2>
        <div className="form-group">
          <label>From</label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select
              value={fromToken}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFromToken(e.target.value)}
            >
              {tokens.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <input
              type="number"
              value={amount}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAmount(e.target.value)}
              placeholder="0.00"
              style={{ flex: 1 }}
            />
          </div>
        </div>
        <div className="form-group">
          <label>To</label>
          <select
            value={toToken}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setToToken(e.target.value)}
          >
            {tokens.map(t => <option key={t} value={t}>{t}</option>)}
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
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSlippage(e.target.value)}
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
            <div className="stat-label">ETH → USDC</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">BRDG → USDC</div>
          </div>
          <div className="stat">
            <div className="stat-value">$0.00</div>
            <div className="stat-label">SOL → ETH</div>
          </div>
        </div>
      </div>
    </div>
  )
}
