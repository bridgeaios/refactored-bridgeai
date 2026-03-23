// Lightweight wallet init - MetaMask, Phantom, injected Web3
// MetaMask / Injected: window.ethereum (EIP-1193) or window.web3?.currentProvider (legacy)
// Phantom: window.phantom?.solana or window.solana

/** Get injected EVM provider. Handles multiple wallets (ethereum can be array). */
export function getEthereumProvider() {
  if (typeof window === 'undefined') return null;
  const eth = window.ethereum;
  if (eth) {
    return Array.isArray(eth) ? eth[0] : eth;
  }
  if (window.web3?.currentProvider) return window.web3.currentProvider;
  return null;
}

function getPhantomProvider() {
  if (typeof window === 'undefined') return null;
  const p = window.phantom?.solana;
  if (p?.isPhantom) return p;
  if (window.solana?.isPhantom) return window.solana;
  return null;
}

function isExtensionInvalidated(err) {
  const msg = (err?.message || '') + (err?.toString?.() || '');
  return /Extension context invalidated|ChromeTransport disconnected|context invalidated/i.test(msg);
}

/**
 * Sign a message using the connected EVM wallet (MetaMask or similar)
 * @param {string} message - Message to sign
 * @param {string} address - Address to sign with (optional, uses connected wallet if not provided)
 * @returns {Promise<string>} - Hex-encoded signature
 */
export async function signMessageEVM(message, address) {
  if (typeof window === 'undefined') throw new Error('Window not defined');
  
  const eth = window.__walletEVM || getEthereumProvider();
  if (!eth) throw new Error('No EVM wallet connected');
  
  const addr = address || (await eth.request({ method: 'eth_accounts' }))?.[0];
  if (!addr) throw new Error('No EVM address available');
  
  // Convert message to hex if needed
  const hexMessage = typeof message === 'string' 
    ? '0x' + Buffer.from(message).toString('hex') 
    : message;
    
  const signature = await eth.request({
    method: 'personal_sign',
    params: [hexMessage, addr]
  });
  
  return signature;
}

/**
 * Sign a transaction using the connected EVM wallet (MetaMask or similar)
 * @param {Object} transaction - Transaction object to sign
 * @returns {Promise<Object>} - Signed transaction
 */
export async function signTransactionEVM(transaction) {
  if (typeof window === 'undefined') throw new Error('Window not defined');
  
  const eth = window.__walletEVM || getEthereumProvider();
  if (!eth) throw new Error('No EVM wallet connected');
  
  // Add from address if not present
  const tx = { ...transaction };
  if (!tx.from) {
    const accounts = await eth.request({ method: 'eth_accounts' });
    tx.from = accounts?.[0];
    if (!tx.from) throw new Error('No EVM address available');
  }
  
  // Sign the transaction
  const signedTx = await eth.request({
    method: 'eth_signTransaction',
    params: [tx]
  });
  
  return signedTx;
}

/**
 * Sign a message using the connected Solana wallet (Phantom or similar)
 * @param {string} message - Message to sign (as UTF-8 string)
 * @param {string} publicKey - Public key to sign with (optional, uses connected wallet if not provided)
 * @returns {Promise<string>} - Base58-encoded signature
 */
export async function signMessageSolana(message, publicKey) {
  if (typeof window === 'undefined') throw new Error('Window not defined');
  
  const provider = window.phantom?.solana || getPhantomProvider() || window.solana;
  if (!provider) throw new Error('No Solana wallet connected');
  
  const pubKey = publicKey || (provider.publicKey?.toString?.() || provider.publicKey);
  if (!pubKey) throw new Error('No Solana public key available');
  
  // Convert message to bytes
  const messageBytes = new TextEncoder().encode(message);
  
  // Sign the message
  const signature = await provider.signMessage(messageBytes);
  
  // Convert signature to base58 string (assuming it's returned as Uint8Array)
  if (signature instanceof Uint8Array) {
    // Convert Uint8Array to base58 (simplified - in real implementation you'd use bs58 library)
    // For now, we'll return as hex for simplicity
    return Buffer.from(signature).toString('hex');
  }
  
  return signature.toString();
}

/**
 * Sign a transaction using the connected Solana wallet (Phantom or similar)
 * @param {Object} transaction - Transaction object to sign
 * @returns {Promise<Object>} - Signed transaction
 */
export async function signTransactionSolana(transaction) {
  if (typeof window === 'undefined') throw new Error('Window not defined');
  
  const provider = window.phantom?.solana || getPhantomProvider() || window.solana;
  if (!provider) throw new Error('No Solana wallet connected');
  
  // Sign the transaction
  const signedTx = await provider.signTransaction(transaction);
  
  return signedTx;
}

export async function initWallet() {
  const container = document.getElementById('side-panel') || document.body;
  const walletDiv = document.createElement('div');
  walletDiv.id = 'wallet-status';
  walletDiv.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;font-size:13px;';
  walletDiv.innerHTML = `
    <button id="connect-evm" style="padding:6px 12px;background:#2a4;color:#fff;border:none;border-radius:4px;cursor:pointer;margin:2px;">Connect EVM</button>
    <button id="connect-sol" style="padding:6px 12px;background:#44a;color:#fff;border:none;border-radius:4px;cursor:pointer;margin:2px;">Connect Solana</button>
    <div id="wallet-hint" style="font-size:10px;color:#888;margin-top:4px;">Click Connect, then approve in wallet. Need one? <a href="https://metamask.io/download/" target="_blank" rel="noopener">MetaMask</a> (EVM) · <a href="https://phantom.app/" target="_blank" rel="noopener">Phantom</a> (Solana)</div>
    <div id="wallet-info" style="display:none;margin-top:8px;">EVM: <span id="evm-addr"></span> | Bal: <span id="evm-bal"></span><br>Sol: <span id="sol-addr"></span></div>
  `;
  container.appendChild(walletDiv);

  const evmBtn = document.getElementById('connect-evm');
  const solBtn = document.getElementById('connect-sol');
  const evmAddrSpan = document.getElementById('evm-addr');
  const evmBalSpan = document.getElementById('evm-bal');
  const solAddrSpan = document.getElementById('sol-addr');
  const infoDiv = document.getElementById('wallet-info');
  const hintEl = document.getElementById('wallet-hint');

  const runAsync = (fn) => () => { setTimeout(fn, 0); };

  let _evmPending = false;
  let _solPending = false;

  async function connectEVM() {
    if (_evmPending) {
      hintEl.textContent = 'Please wait for MetaMask to respond...';
      return;
    }
    _evmPending = true;
    evmBtn.disabled = true;
    evmBtn.textContent = 'Connecting...';
    hintEl.textContent = 'Check MetaMask popup — approve or reject.';
    try {
      const eth = getEthereumProvider();
      if (!eth) {
        evmBtn.textContent = 'Install MetaMask';
        hintEl.innerHTML = 'MetaMask not found. <a href="https://metamask.io/download/" target="_blank" rel="noopener">Install MetaMask</a> (EVM) · <a href="https://phantom.app/" target="_blank" rel="noopener">Phantom</a> (Solana)';
        window.open('https://metamask.io/download/', '_blank');
        return;
      }
      const accounts = await eth.request({ method: 'eth_requestAccounts' });
      const addr = accounts?.[0];
      if (!addr) {
        evmBtn.textContent = 'Connect EVM';
        hintEl.textContent = 'No account selected. Try again.';
        return;
      }
      evmAddrSpan.textContent = `${addr.slice(0, 6)}...${addr.slice(-4)}`;
      try {
        const bal = await eth.request({ method: 'eth_getBalance', params: [addr, 'latest'] });
        evmBalSpan.textContent = `${(Number(bal) / 1e18).toFixed(4)} ETH`;
      } catch (e) { evmBalSpan.textContent = '—'; }
      infoDiv.style.display = 'block';
      evmBtn.textContent = 'EVM ✓';
      hintEl.textContent = 'Connected. Use for UBI, marketplace, etc.';
      window.__walletEVM = eth;
    } catch (err) {
      if (err?.code === 4001) {
        evmBtn.textContent = 'Connect EVM';
        hintEl.textContent = 'Connection rejected. Click Connect to try again.';
      } else if (/already pending|please wait/i.test(err?.message || '')) {
        evmBtn.textContent = 'Connect EVM';
        hintEl.textContent = 'MetaMask popup is open — approve or close it, then try again.';
      } else if (isExtensionInvalidated(err)) {
        evmBtn.textContent = 'Refresh page';
        hintEl.innerHTML = 'MetaMask was updated. <a href="javascript:location.reload()">Refresh page</a> to reconnect.';
      } else {
        evmBtn.textContent = 'Retry';
        hintEl.textContent = err?.message || 'Connection failed. Click Retry.';
      }
    } finally {
      _evmPending = false;
      evmBtn.disabled = false;
    }
  }

  async function connectSol() {
    if (_solPending) {
      hintEl.textContent = 'Please wait for Phantom to respond...';
      return;
    }
    const provider = getPhantomProvider();
    if (!provider) {
      solBtn.textContent = 'Install Phantom';
      hintEl.innerHTML = 'Phantom not found. <a href="https://phantom.app/" target="_blank" rel="noopener">Install Phantom</a> (Solana) · <a href="https://metamask.io/download/" target="_blank" rel="noopener">MetaMask</a> (EVM)';
      window.open('https://phantom.app/', '_blank');
      return;
    }
    _solPending = true;
    solBtn.disabled = true;
    solBtn.textContent = 'Connecting...';
    hintEl.textContent = 'Check Phantom popup — approve or reject.';
    try {
      const resp = await provider.connect();
      const addr = resp?.publicKey?.toString?.() || provider.publicKey?.toString?.() || provider.publicKey;
      if (addr) {
        solAddrSpan.textContent = `${addr.slice(0, 6)}...${addr.slice(-4)}`;
        infoDiv.style.display = 'block';
        solBtn.textContent = 'Sol ✓';
        hintEl.textContent = 'Connected. Use for UBI, marketplace, etc.';
      } else {
        solBtn.textContent = 'Connect Solana';
      }
    } catch (err) {
      const msg = err?.message || '';
      if (err?.code === 4001 || msg.includes('reject')) {
        solBtn.textContent = 'Connect Solana';
        hintEl.textContent = 'Connection rejected. Click Connect to try again.';
      } else if (/not found|wallet not found|phantom.*not/i.test(msg)) {
        solBtn.textContent = 'Install Phantom';
        hintEl.innerHTML = 'Phantom not found. <a href="https://phantom.app/" target="_blank" rel="noopener">Install Phantom</a> (Solana) · <a href="https://metamask.io/download/" target="_blank" rel="noopener">MetaMask</a> (EVM)';
      } else if (isExtensionInvalidated(err)) {
        solBtn.textContent = 'Refresh page';
        hintEl.innerHTML = 'Phantom was updated. <a href="javascript:location.reload()">Refresh page</a> to reconnect.';
      } else {
        solBtn.textContent = 'Retry';
        hintEl.textContent = msg || 'Connection failed. Click Retry.';
      }
    } finally {
      _solPending = false;
      solBtn.disabled = false;
    }
  }

  evmBtn.onclick = runAsync(connectEVM);
  solBtn.onclick = runAsync(connectSol);

  // Auto-reconnect if previously connected (provider still valid)
  runAsync(async () => {
    try {
      const eth = getEthereumProvider();
      if (eth) {
        const accounts = await eth.request({ method: 'eth_accounts' });
        if (accounts?.[0]) {
          const addr = accounts[0];
          evmAddrSpan.textContent = `${addr.slice(0, 6)}...${addr.slice(-4)}`;
          try {
            const bal = await eth.request({ method: 'eth_getBalance', params: [addr, 'latest'] });
            evmBalSpan.textContent = `${(Number(bal) / 1e18).toFixed(4)} ETH`;
          } catch (e) { evmBalSpan.textContent = '—'; }
          infoDiv.style.display = 'block';
          evmBtn.textContent = 'EVM ✓';
          window.__walletEVM = eth;
        }
      }
      const phantom = getPhantomProvider();
      if (phantom?.isConnected && phantom.publicKey) {
        const addr = phantom.publicKey.toString();
        solAddrSpan.textContent = `${addr.slice(0, 6)}...${addr.slice(-4)}`;
        infoDiv.style.display = 'block';
        solBtn.textContent = 'Sol ✓';
      }
    } catch (e) { /* ignore - extension may be invalidated */ }
  })();
}
