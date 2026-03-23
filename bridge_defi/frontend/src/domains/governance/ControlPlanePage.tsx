import { useMemo, useState } from 'react';

type AuditItem = {
  id: string;
  domain: string;
  status: 'passing' | 'warning' | 'failing';
  detail: string;
};

const INITIAL_AUDIT: AuditItem[] = [
  { id: 'g-1', domain: 'OpenAPI drift', status: 'passing', detail: 'No drift detected in the curated contract set.' },
  { id: 'g-2', domain: 'Route coverage', status: 'warning', detail: 'Some planned routes are still stubbed in the current frontend tree.' },
  { id: 'g-3', domain: 'Reputation feed', status: 'passing', detail: 'Top reputation data is available for the control plane.' },
];

function statusLabel(status: AuditItem['status']) {
  if (status === 'passing') return 'Passing';
  if (status === 'warning') return 'Warning';
  return 'Failing';
}

function statusClass(status: AuditItem['status']) {
  if (status === 'passing') return 'status-passing';
  if (status === 'warning') return 'status-warning';
  return 'status-failing';
}

export function ControlPlanePage() {
  const [audits] = useState<AuditItem[]>(INITIAL_AUDIT);
  const passingCount = useMemo(() => audits.filter((item) => item.status === 'passing').length, [audits]);
  const warningCount = useMemo(() => audits.filter((item) => item.status === 'warning').length, [audits]);
  const failingCount = useMemo(() => audits.filter((item) => item.status === 'failing').length, [audits]);

  return (
    <div className="control-plane-page">
      <h1>Control Plane</h1>
      <p>Governance surface for drift, reputation, and policy checks.</p>

      <section className="card">
        <h2>Drift Audit</h2>
        <div className="grid">
          <div className="stat">
            <div className="stat-value">{passingCount}</div>
            <div className="stat-label">Passing</div>
          </div>
          <div className="stat">
            <div className="stat-value">{warningCount}</div>
            <div className="stat-label">Warnings</div>
          </div>
          <div className="stat">
            <div className="stat-value">{failingCount}</div>
            <div className="stat-label">Failing</div>
          </div>
        </div>
        <div className="stack">
          {audits.map((item) => (
            <article key={item.id} className="card">
              <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
                <h3 style={{ margin: 0 }}>{item.domain}</h3>
                <span className={statusClass(item.status)}>{statusLabel(item.status)}</span>
              </header>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Top Reputation</h2>
        <pre>{JSON.stringify(
          [
            { id: 'agent-01', name: 'Alpha', score: 98 },
            { id: 'agent-02', name: 'Beta', score: 91 },
            { id: 'agent-03', name: 'Gamma', score: 88 },
          ],
          null,
          2,
        )}</pre>
      </section>
    </div>
  );
}
