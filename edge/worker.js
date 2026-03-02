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

    const jsonResponse = (data, status = 200) => new Response(JSON.stringify(data), {
      status,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
        "X-Edge-Ray": ray,
        "Server": "cloudflare",
      },
    });

    const base64UrlDecode = (str) => {
      str = str.replace(/-/g, '+').replace(/_/g, '/');
      while (str.length % 4) str += '=';
      return atob(str);
    };

    const verifyJWT = async (token) => {
      if (!token || !token.startsWith("Bearer ")) {
        return { valid: false, error: "Missing or invalid token format" };
      }

      const tokenValue = token.slice(7);

      try {
        const parts = tokenValue.split(".");
        if (parts.length !== 3) {
          return { valid: false, error: "Invalid token structure" };
        }

        const [headerB64, payloadB64, signatureB64] = parts;

        const header = JSON.parse(base64UrlDecode(headerB64));
        const payload = JSON.parse(base64UrlDecode(payloadB64));

        const signingInput = `${headerB64}.${payloadB64}`;
        const signature = base64UrlDecode(signatureB64);

        const secret = env.JWT_SECRET;
        const algorithm = header.alg;

        let signatureValid = false;

        if (algorithm === 'HS256') {
          const encoder = new TextEncoder();
          const keyData = await crypto.subtle.importKey(
            "raw",
            encoder.encode(secret),
            { name: "HMAC", hash: "SHA-256" },
            false,
            ["verify"]
          );
          signatureValid = await crypto.subtle.verify(
            "HMAC",
            keyData,
            signature,
            encoder.encode(signingInput)
          );
        } else if (algorithm === 'RS256' || algorithm === 'ES256') {
          const publicKeyPem = env.JWT_PUBLIC_KEY;
          if (!publicKeyPem) {
            return { valid: false, error: "Public key not configured" };
          }
          
          const algorithmName = algorithm === 'RS256' ? 'RSA-SHA256' : 'ECDSA';
          const keyData = await crypto.subtle.importKey(
            "spki",
            base64UrlDecode(publicKeyPem),
            { name: algorithmName, hash: "SHA-256" },
            false,
            ["verify"]
          );
          signatureValid = await crypto.subtle.verify(
            algorithmName,
            keyData,
            signature,
            encoder.encode(signingInput)
          );
        } else {
          return { valid: false, error: `Unsupported algorithm: ${algorithm}` };
        }

        if (!signatureValid) {
          log(401, { event: "invalid_signature", user_id: payload.sub });
          return { valid: false, error: "Invalid signature" };
        }

        if (payload.exp && Date.now() > payload.exp * 1000) {
          log(401, { event: "expired_token", user_id: payload.sub });
          return { valid: false, error: "Token expired" };
        }

        return {
          valid: true,
          user: payload.sub,
          role: payload.role || "user",
          org: payload.org,
        };
      } catch (err) {
        return { valid: false, error: `Token validation failed: ${err.message}` };
      }
    };

    try {
      const url = new URL(request.url);
      const path = url.pathname;

      const allowedRoutes = ['/health', '/edge/health'];
      const isAllowed = allowedRoutes.includes(path) || path === '/';
      
      if (!isAllowed && path !== '/') {
        const knownApiRoutes = [
          '/run-task',
          '/api/distribution/run',
          '/api/execution/',
          '/api/me',
          '/internal/treasury/summary',
        ];
        
        const isKnownRoute = knownApiRoutes.some(route => 
          path === route || path.startsWith(route)
        );
        
        if (!isKnownRoute) {
          log(404, { blocked: "unknown_route", path });
          return jsonResponse({ 
            error: "Not Found",
            detail: `Route ${path} not recognized`,
            requestId 
          }, 404);
        }
      }

      if (path === "/health" || path === "/edge/health") {
        return jsonResponse({
          status: "healthy",
          worker: "bridge-edge",
          requestId,
          timestamp: new Date().toISOString(),
        });
      }

      const authHeader = request.headers.get("Authorization");
      const publicRoutes = ['/health', '/edge/health', '/run-task'];
      
      if (!publicRoutes.includes(path) && path !== '/') {
        if (!authHeader) {
          log(401, { blocked: "missing_auth", path });
          return jsonResponse({ 
            error: "Unauthorized",
            detail: "Authorization required",
            requestId 
          }, 401);
        }

        const jwt = await verifyJWT(authHeader);
        
        if (!jwt.valid) {
          log(401, { blocked: "invalid_token", error: jwt.error, path });
          return jsonResponse({ 
            error: "Unauthorized",
            detail: jwt.error,
            requestId 
          }, 401);
        }

        if (path.startsWith('/internal/') && jwt.role !== 'admin') {
          log(403, { blocked: "non_admin", path, role: jwt.role });
          return jsonResponse({ 
            error: "Forbidden",
            detail: "Admin access required",
            requestId 
          }, 403);
        }

        request.headers.set("X-User-ID", jwt.user);
        request.headers.set("X-User-Role", jwt.role);
        request.headers.set("X-User-Org", jwt.org || "");
      }

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

      return new Response(responseBody, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": requestId,
          "X-Edge-Ray": ray,
          "Server": "cloudflare",
        },
      });

    } catch (err) {
      log(500, { error: err.message });
      return jsonResponse({ 
        error: "Edge Error",
        detail: err.message,
        requestId 
      }, 500);
    }
  },
};
