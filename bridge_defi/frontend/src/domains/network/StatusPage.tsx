function Badge({ status }: { status: 'online' | 'degraded' | 'offline' | 'unknown' }) {
  return <span className={`status-badge status-${status}`}>{status}</span>;
}

export function StatusPage() {
  const apiStatus: 'online' | 'degraded' | 'offline' | 'unknown' = 'online';
  const capabilities = ['auth', 'telemetry', 'routing', 'swarm-health'];

  return (
    <div className="status-page">
      <h1>System Status</h1>
      <p>Operational snapshot for the network and infra surface.</p>

      <section className="card">
        <h2>API</h2>
        <Badge status={apiStatus} />
      </section>

      <section className="card">
        <h2>Capabilities</h2>
        <pre>{JSON.stringify(capabilities, null, 2)}</pre>
      </section>

      <section className="card">
        <h2>Raw Status</h2>
        <pre>{JSON.stringify({ apiStatus, uptime: '99.9%', region: 'af-south-1' }, null, 2)}</pre>
      </section>
    </div>
  );
}
