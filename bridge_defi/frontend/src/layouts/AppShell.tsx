import { NavLink, Outlet } from 'react-router-dom';
import { useState } from 'react';
import { useWallet } from '../core/hooks/useWallet';

const NAV = [
  { group: 'Platform',    items: [
    { to: '/',          label: 'Home' },
    { to: '/dashboard', label: 'Executive Dashboard' },
    { to: '/apps',      label: '50 Applications' },
  ]},
  { group: 'Economy',     items: [
    { to: '/treasury',  label: 'Treasury' },
    { to: '/cfo',       label: 'CFO' },
    { to: '/lending',   label: 'Lending' },
    { to: '/staking',   label: 'Staking' },
    { to: '/dex',       label: 'DEX' },
  ]},
  { group: 'Twins',       items: [
    { to: '/twin',      label: 'Digital Twin' },
    { to: '/agents',    label: 'Agents & Twins' },
  ]},
  { group: 'Network',     items: [
    { to: '/network',   label: 'Network Dashboard' },
    { to: '/ban',       label: 'BAN Live Wall' },
    { to: '/status',    label: 'Status' },
  ]},
  { group: 'Governance',  items: [
    { to: '/control',   label: 'Control Plane' },
  ]},
  { group: 'Infra',       items: [
    { to: '/settings',  label: 'Settings' },
    { to: '/docs',      label: 'Docs' },
  ]},
] as const;

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { isConnected, address, connect, disconnect, isConnecting } = useWallet();

  return (
    <div className="appshell" data-sidebar={sidebarOpen ? 'open' : 'closed'}>
      <aside className="appshell-sidebar">
        <div className="appshell-logo">
          <img src="/bridge-logo.svg" alt="Bridge AI OS" width={32} height={32} />
          {sidebarOpen && <span>Bridge AI OS</span>}
        </div>
        <nav className="appshell-nav">
          {NAV.map(({ group, items }) => (
            <div key={group} className="nav-group">
              {sidebarOpen && <span className="nav-group-label">{group}</span>}
              {items.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                  title={label}
                >
                  {sidebarOpen ? label : label[0]}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="appshell-content">
        <header className="appshell-topbar">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(v => !v)}
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {sidebarOpen ? '←' : '→'}
          </button>
          <div className="topbar-actions">
            <button
              className="connect-btn"
              onClick={isConnected ? disconnect : connect}
              disabled={isConnecting}
            >
              {isConnecting
                ? 'Connecting...'
                : isConnected
                  ? `${address?.slice(0, 6)}…${address?.slice(-4)}`
                  : 'Connect Wallet'}
            </button>
          </div>
        </header>
        <main className="appshell-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
