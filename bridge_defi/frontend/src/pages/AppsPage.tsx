const appRoutes = [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/treasury', label: 'Treasury' },
]

export function AppsPage() {
  return (
    <section className="page apps-page">
      <div className="card">
        <h1>Apps</h1>
        <p>Top-level routes currently wired in this phase.</p>
        <ul style={{ marginTop: '1rem', paddingLeft: '1.25rem' }}>
          {appRoutes.map((route) => (
            <li key={route.to}>
              {route.label} - {route.to}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
