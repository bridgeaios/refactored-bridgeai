export function DocsPage() {
  return (
    <div className="docs-page">
      <h1>Documentation</h1>
      <p>Reference entry points for the frontend refactor.</p>

      <section className="card">
        <h2>OpenAPI</h2>
        <p>
          The public contract is expected at{' '}
          <a href="/contracts/openapi.v2.public.json" target="_blank" rel="noreferrer">
            /contracts/openapi.v2.public.json
          </a>
          .
        </p>
      </section>

      <section className="card">
        <h2>System Map</h2>
        <p>
          The system map is expected at{' '}
          <a href="http://localhost:4201/system-map.html" target="_blank" rel="noreferrer">
            http://localhost:4201/system-map.html
          </a>
          .
        </p>
      </section>
    </div>
  );
}
