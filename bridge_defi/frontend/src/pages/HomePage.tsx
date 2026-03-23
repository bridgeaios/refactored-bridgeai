import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <section className="page home-page">
      <div className="card">
        <h1>Bridge AI OS</h1>
        <p>Phase 4 top-level shell. Use the dashboard for overview and Apps for route entry points.</p>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1rem' }}>
          <Link className="btn" to="/dashboard">
            Open Dashboard
          </Link>
          <Link className="btn" to="/apps">
            Open Apps
          </Link>
        </div>
      </div>
    </section>
  )
}
