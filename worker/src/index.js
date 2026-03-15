/**
 * Bridge Live Wall — Cloudflare Worker
 * Health + optional R2 (list/head). Use same R2_BUCKET_NAME in .env as bucket_name in wrangler.toml.
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/$/, "") || "/";

    // GET / or /health — health check for DNS/audit
    if (request.method === "GET" && (path === "" || path === "/" || path === "/health")) {
      return Response.json({
        ok: true,
        service: "bridge-live-wall-api",
        worker: true,
        r2: !!env.BUCKET,
      }, { status: 200, headers: { "Access-Control-Allow-Origin": "*" } });
    }

    // GET /r2/list — list R2 keys (optional; requires BUCKET binding)
    if (request.method === "GET" && path === "/r2/list" && env.BUCKET) {
      try {
        const list = await env.BUCKET.list({ limit: 100 });
        return Response.json({
          ok: true,
          keys: list.objects.map((o) => o.key),
          truncated: list.truncated,
        }, { status: 200, headers: { "Access-Control-Allow-Origin": "*" } });
      } catch (e) {
        return Response.json({ ok: false, error: String(e.message) }, { status: 500, headers: { "Access-Control-Allow-Origin": "*" } });
      }
    }

    // 404
    return new Response(JSON.stringify({ ok: false, error: "Not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
    });
  },
};
