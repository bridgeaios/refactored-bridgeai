function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export function NetworkDashboardPage() {
  const swarmHealth = {
    status: 'healthy',
    nodes: 12,
    latencyMs: 38,
  };

  const liveMap = {
    regions: ['us-east', 'eu-west', 'af-south'],
    edges: 24,
    activeRoutes: 9,
  };

  return (
    <div className="network-page">
      <h1>Network Dashboard</h1>
      <p>Swarm telemetry, live map status, and routing snapshots.</p>

      <div className="grid">
        <Stat label="Swarm" value={swarmHealth.status} />
        <Stat label="Nodes" value={String(swarmHealth.nodes)} />
        <Stat label="Latency" value={`${swarmHealth.latencyMs}ms`} />
      </div>

      <section className="card">
        <h2>Swarm Health</h2>
        <pre>{JSON.stringify(swarmHealth, null, 2)}</pre>
      </section>

      <section className="card">
        <h2>Live Map</h2>
        <pre>{JSON.stringify(liveMap, null, 2)}</pre>
      </section>
    </div>
  );
}
