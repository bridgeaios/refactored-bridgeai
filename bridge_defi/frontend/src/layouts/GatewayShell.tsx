import { Outlet } from 'react-router-dom';

export function GatewayShell() {
  return (
    <div className="gateway-shell">
      <header className="gateway-header">
        <img src="/bridge-logo.svg" alt="Bridge AI OS" width={40} height={40} />
        <h1>Bridge AI OS</h1>
      </header>
      <main className="gateway-main">
        <Outlet />
      </main>
    </div>
  );
}
