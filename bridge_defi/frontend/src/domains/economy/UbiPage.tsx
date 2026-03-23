import { useWallet } from '../../hooks/useWallet'

export function UbiPage() {
  const { isConnected } = useWallet()

  return (
    <div className="ubi">
      <div className="card">
        <h1>UBI</h1>
        <p>{isConnected ? 'Ready to distribute' : 'Wallet not connected'}</p>
        <button className="btn" disabled={!isConnected}>
          Distribute UBI
        </button>
      </div>
    </div>
  )
}
