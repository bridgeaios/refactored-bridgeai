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

      // UNKNOWN ROUTES → 404 (not 500)
      const allowedRoutes = [
        '/health',
        '/edge/health',
        '/run-task',
        '/api/distribution/run',
        '/api/execution/',
        '/api/me',
        '/internal/treasury/summary',
      ];
      
      const isAllowed = allowedRoutes.some(route => {
        if (route.endsWith('/')) return path.startsWith(route);
        return path === route || path.startsWith(route + '/');
      });
      
      if (!isAllowed && path !== '/') {
        log(404, { blocked: "unknown_route", path });
        return new Response(JSON.stringify({ 
          error: "Not Found",
          detail: `Route ${path} not recognized`,
          requestId 
        }), {
          status: 404,
          headers: { 
            "Content-Type": "application/json",
            "X-Request-ID": requestId,
            "X-Edge-Ray": ray,
          },
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
          headers: { 
            "Content-Type": "application/json",
            "X-Request-ID": requestId,
            "X-Edge-Ray": ray,
          },
        });
      }

      // AUTH GATE: Validate JWT (placeholder - replace with real validation)
      const authHeader = request.headers.get("Authorization");
      
      // Public routes that don't require auth
      const publicRoutes = ['/health', '/edge/health'];
      if (!publicRoutes.includes(path) && path !== '/') {
        if (!authHeader) {
          log(401, { blocked: "missing_auth", path });
          return new Response(JSON.stringify({ 
            error: "Unauthorized",
            detail: "Authorization required",
            requestId 
          }), {
            status: 401,
            headers: { 
              "Content-Type": "application/json",
              "X-Request-ID": requestId,
              "X-Edge-Ray": ray,
            },
          });
        }
      }

      // FORWARD TO BACKEND
      const backendUrl = env.BACKEND_URL || "http://backend:8000";
      const forwardUrl = `${backendUrl}${path}${url.search}`;

      const forwardHeaders = new Headers(request.headers);
      forwardHeaders.set("X-Edge-Authorized", "true");
      forwardHeaders.set("X-Request-ID", requestId);
      forwardHeaders.set("X-Edge-Ray", ray);
      forwardHeaders.delete("cf-ray");

      const response = await fetch(forwardUrl, {
        method: request.method,
        headers: forwardHeaders,
        body: request.body,
        redirect: "manual",
      });

      log(response.status, { path });
      
      const responseBody = await response.text();
      const responseHeaders = new Headers();
      responseHeaders.set("Content-Type", "application/json");
      responseHeaders.set("X-Request-ID", requestId);
      responseHeaders.set("X-Edge-Ray", ray);
      responseHeaders.set("Server", "cloudflare");

      return new Response(responseBody, {
        status: response.status,
        headers: responseHeaders,
      });

    } catch (err) {
      log(500, { error: err.message, stack: err.stack });
      return new Response(JSON.stringify({ 
        error: "Edge Error",
        detail: err.message,
        requestId 
      }), {
        status: 500,
        headers: { 
          "Content-Type": "application/json",
          "X-Request-ID": requestId,
          "X-Edge-Ray": ray,
          "Server": "cloudflare",
        },
      });
    }
  },
};
