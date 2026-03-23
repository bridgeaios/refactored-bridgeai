import { useState, type ChangeEvent } from 'react';

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export function AgentsPage() {
  const [query, setQuery] = useState('');

  const twins = [
    { id: 'twin-alpha', name: 'Alpha', state: 'ALIVE', score: '98' },
    { id: 'twin-beta', name: 'Beta', state: 'STANDBY', score: '87' },
  ];

  const filteredTwins = twins.filter((twin) => {
    const needle = query.trim().toLowerCase();
    return (
      needle.length === 0 ||
      twin.name.toLowerCase().includes(needle) ||
      twin.id.toLowerCase().includes(needle)
    );
  });

  return (
    <div className="agents-page">
      <h1>Agents &amp; Twins</h1>
      <p>Live roster and leaderboard surface for the digital twin domain.</p>

      <section className="card">
        <h2>Overview</h2>
        <div className="grid">
          <Stat label="Active Twins" value="2" />
          <Stat label="Online" value="1" />
          <Stat label="Leaderboard Leader" value="Alpha" />
        </div>
      </section>

      <section className="card">
        <h2>Active Twins</h2>
        <label className="form-group">
          <span>Search</span>
          <input
            type="text"
            value={query}
            onChange={(event: ChangeEvent<HTMLInputElement>) => setQuery(event.target.value)}
            placeholder="Filter twins by name or id"
          />
        </label>
        <pre>{JSON.stringify(filteredTwins, null, 2)}</pre>
      </section>

      <section className="card">
        <h2>Leaderboard</h2>
        <pre>{JSON.stringify(filteredTwins.map((twin, index) => ({
          rank: index + 1,
          id: twin.id,
          score: twin.score,
        })), null, 2)}</pre>
      </section>
    </div>
  );
}
