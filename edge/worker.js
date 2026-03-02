export default {
  async fetch(request, env, ctx) {
    const start = Date.now();
    const requestId = crypto.randomUUID();
    const ray = request.headers.get("cf-ray") || "unknown";

    const log = (status, extra = {}) => {
      const entry = {
        requestId,
        ray,
        method: request.method,
        url: request.url,
        status,
        duration: Date.now() - start,
        timestamp: new Date().toISOString(),
        ...extra,
      };
      console.log(JSON.stringify(entry));
    };

    try {
      const url = new URL(request.url);
      const path = url.pathname;

      // BLOCK: Direct access to backend endpoints without worker
      if (path.startsWith("/run-task") && !request.headers.get("x-edge-authorized")) {
        log(401, { blocked: "unauthorized_origin" });
        return new Response(JSON.stringify({ error: "Unauthorized: Must pass through edge" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        });
      }

      // HEALTH CHECK
      if (path === "/health" || path === "/edge/health") {
        return new Response(JSON.stringify({
          status: "healthy",
          worker: "bridge-edge",
          requestId,
          timestamp: new Date().toISOString(),
        }), {
          headers: { "Content-Type": "application/json" },
        });
      }

      // AUTH GATE: Validate JWT (placeholder - replace with real validation)
      const authHeader = request.headers.get("Authorization");
      if (!authHeader && path.startsWith("/api/")) {
        log(401, { blocked: "missing_auth" });
        return new Response(JSON.stringify({ error: "Authorization required" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        });
      }

      // FORWARD TO BACKEND
      const backendUrl = env.BACKEND_URL || "http://backend:8000";
      const forwardUrl = `${backendUrl}${path}`;

      const forwardHeaders = new Headers(request.headers);
      forwardHeaders.set("X-Edge-Authorized", "true");
      forwardHeaders.set("X-Request-ID", requestId);
      forwardHeaders.set("X-Edge-Ray", ray);
      forwardHeaders.delete("cf-ray");

      const response = await fetch(forwardUrl, {
        method: request.method,
        headers: forwardHeaders,
        body: request.body,
      });

      log(response.status);
      return response;

    } catch (err) {
      log(500, { error: err.message });
      return new Response(JSON.stringify({ error: "Edge error", detail: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
