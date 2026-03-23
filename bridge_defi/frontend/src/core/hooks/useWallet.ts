import { useState, useCallback, useEffect } from 'react';

interface WalletState {
  address: string | null;
  chainId: number | null;
  balance: string | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
}

export function useWallet() {
  const [state, setState] = useState<WalletState>({
    address: null,
    chainId: null,
    balance: null,
    isConnected: false,
    isConnecting: false,
    error: null,
  });

  const fetchBalance = useCallback(async (address: string) => {
    try {
      const balance = (await window.ethereum!.request({
        method: 'eth_getBalance',
        params: [address, 'latest'],
      })) as string;

      const ethBalance = (parseInt(balance, 16) / 1e18).toFixed(4);
      return ethBalance;
    } catch {
      return null;
    }
  }, []);

  const connect = useCallback(async () => {
    if (typeof window.ethereum === 'undefined') {
      setState((prev) => ({
        ...prev,
        error: 'MetaMask not installed. Please install MetaMask to connect.',
      }));
      return;
    }

    setState((prev) => ({ ...prev, isConnecting: true, error: null }));

    try {
      const accounts = (await window.ethereum.request({
        method: 'eth_requestAccounts',
      })) as string[];

      const chainId = (await window.ethereum.request({
        method: 'eth_chainId',
      })) as string;

      const account = accounts[0];
      const balance = await fetchBalance(account);

      setState({
        address: account || null,
        chainId: parseInt(chainId, 16),
        balance,
        isConnected: accounts.length > 0,
        isConnecting: false,
        error: null,
      });
    } catch (error) {
      console.error('Failed to connect wallet:', error);
      setState((prev) => ({
        ...prev,
        isConnecting: false,
        error: error instanceof Error ? error.message : 'Failed to connect wallet',
      }));
    }
  }, [fetchBalance]);

  const disconnect = useCallback(() => {
    setState({
      address: null,
      chainId: null,
      balance: null,
      isConnected: false,
      isConnecting: false,
      error: null,
    });
  }, []);

  useEffect(() => {
    if (typeof window.ethereum === 'undefined') return;

    const handleAccountsChanged = (accounts: string[]) => {
      if (accounts.length === 0) {
        disconnect();
      } else {
        setState((prev) => ({
          ...prev,
          address: accounts[0] || null,
          isConnected: accounts.length > 0,
        }));
      }
    };

    const handleChainChanged = (chainId: string) => {
      setState((prev) => ({
        ...prev,
        chainId: parseInt(chainId, 16),
      }));
    };

    const handleDisconnect = (error: { code: number; message: string }) => {
      console.error('MetaMask disconnected:', error);
      disconnect();
    };

    const acctCb = handleAccountsChanged as (...args: unknown[]) => void;
    const chainCb = handleChainChanged as (...args: unknown[]) => void;
    const discCb = handleDisconnect as (...args: unknown[]) => void;

    window.ethereum.on('accountsChanged', acctCb);
    window.ethereum.on('chainChanged', chainCb);
    window.ethereum.on('disconnect', discCb);

    window.ethereum
      .request({ method: 'eth_accounts' })
      .then((accounts: unknown) => {
        const accs = accounts as string[];
        if (accs.length > 0) {
          connect();
        }
      })
      .catch(() => {});

    return () => {
      window.ethereum?.removeListener('accountsChanged', acctCb);
      window.ethereum?.removeListener('chainChanged', chainCb);
      window.ethereum?.removeListener('disconnect', discCb);
    };
  }, [connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
  };
}

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
      on: (event: string, callback: (...args: unknown[]) => void) => void;
      removeListener: (event: string, callback: (...args: unknown[]) => void) => void;
      isMetaMask?: boolean;
    };
  }
}
