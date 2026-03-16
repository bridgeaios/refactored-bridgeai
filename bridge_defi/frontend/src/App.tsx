import { Routes, Route, Link } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import Lending from './components/Lending'
import Staking from './components/Staking'
import Dex from './components/Dex'
import Treasury from './components/Treasury'
import { useWallet } from './hooks/useWallet'
import './index.css'

function App() {
  const { isConnected, address, connect, disconnect } = useWallet()

  const handleConnect = () => {
    if (isConnected) {
      disconnect()
    } else {
      connect()
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Bridge DeFi</h1>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/lending">Lending</Link>
          <Link to="/staking">Staking</Link>
          <Link to="/dex">DEX</Link>
          <Link to="/treasury">Treasury</Link>
        </nav>
        <button className="connect-btn" onClick={handleConnect}>
          {isConnected 
            ? `${address?.slice(0, 6)}...${address?.slice(-4)}` 
            : 'Connect Wallet'}
        </button>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard isConnected={isConnected} />} />
          <Route path="/lending" element={<Lending isConnected={isConnected} />} />
          <Route path="/staking" element={<Staking isConnected={isConnected} />} />
          <Route path="/dex" element={<Dex isConnected={isConnected} />} />
          <Route path="/treasury" element={<Treasury isConnected={isConnected} />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
