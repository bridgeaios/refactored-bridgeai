import { useState, useCallback, useEffect } from 'react'

interface WalletState {
  address: string | null
  chainId: number | null
  balance: string | null
  isConnected: boolean
}

export function useWallet() {
  const [state, setState] = useState<WalletState>({
    address: null,
    chainId: null,
    balance: null,
    isConnected: false
  })

  const connect = useCallback(async () => {
    if (typeof window.ethereum === 'undefined') {
      console.error('MetaMask not installed')
      return
    }

    try {
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts'
      })
      const chainId = await window.ethereum.request({
        method: 'eth_chainId'
      })

      setState({
        address: accounts[0] || null,
        chainId: parseInt(chainId, 16),
        balance: null,
        isConnected: true
      })
    } catch (error) {
      console.error('Failed to connect wallet:', error)
    }
  }, [])

  const disconnect = useCallback(() => {
    setState({
      address: null,
      chainId: null,
      balance: null,
      isConnected: false
    })
  }, [])

  useEffect(() => {
    if (typeof window.ethereum === 'undefined') return

    const handleAccountsChanged = (accounts: string[]) => {
      setState(prev => ({
        ...prev,
        address: accounts[0] || null,
        isConnected: accounts.length > 0
      }))
    }

    const handleChainChanged = (chainId: string) => {
      setState(prev => ({
        ...prev,
        chainId: parseInt(chainId, 16)
      }))
    }

    window.ethereum.on('accountsChanged', handleAccountsChanged)
    window.ethereum.on('chainChanged', handleChainChanged)

    return () => {
      window.ethereum.removeListener('accountsChanged', handleAccountsChanged)
      window.ethereum.removeListener('chainChanged', handleChainChanged)
    }
  }, [])

  return {
    ...state,
    connect,
    disconnect
  }
}

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] }) => Promise<unknown>
      on: (event: string, callback: (...args: unknown[]) => void) => void
      removeListener: (event: string, callback: (...args: unknown[]) => void) => void
    }
  }
}
