export function MarketplacePage() {
  return (
    <div className="marketplace">
      <div className="card">
        <h1>Marketplace</h1>
        <h2>Open Tasks</h2>
        <pre>
          {JSON.stringify(
            [
              {
                id: 'task-1',
                title: 'Write docs',
                status: 'open',
              },
            ],
            null,
            2,
          )}
        </pre>
      </div>
    </div>
  )
}
