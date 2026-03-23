function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export function BanPage() {
  const projects = [
    { id: 'proj-01', name: 'Bridge Live Wall', status: 'active' },
    { id: 'proj-02', name: 'System Map', status: 'watching' },
  ];

  const liveReport = {
    window: '15m',
    incidents: 0,
    warnings: 2,
  };

  return (
    <div className="ban-page">
      <h1>BAN Live Wall</h1>
      <p>Projects, report stream, and operational signal for the live wall.</p>

      <div className="grid">
        <Stat label="Projects" value={String(projects.length)} />
        <Stat label="Incidents" value={String(liveReport.incidents)} />
        <Stat label="Warnings" value={String(liveReport.warnings)} />
      </div>

      <section className="card">
        <h2>Projects</h2>
        <pre>{JSON.stringify(projects, null, 2)}</pre>
      </section>

      <section className="card">
        <h2>Live Report</h2>
        <pre>{JSON.stringify(liveReport, null, 2)}</pre>
      </section>
    </div>
  );
}
