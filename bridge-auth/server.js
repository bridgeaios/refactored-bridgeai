/**
 * Bridge Auth — Identity & Authority Layer
 *
 * SIWE verification, replay protection, short-lived JWT + refresh rotation,
 * WebSocket push for contract events.
 *
 * QR → Wallet → Signature → Role Check → Session Token → Live Contract Sync
 */
import express from "express";
import cors from "cors";
import helmet from "helmet";
import Redis from "ioredis";
import { createAuthRouter } from "./routes/auth.js";
import { attachWebSocket } from "./websocket/events.js";
import config from "./config.js";

const NODE_ENV = (process.env.NODE_ENV || "development").toLowerCase();
if (!["development", "test", "production"].includes(NODE_ENV)) {
  throw new Error(`Invalid NODE_ENV: ${process.env.NODE_ENV}`);
}

// Fail-fast on dangerous production defaults / missing secrets.
if (NODE_ENV === "production") {
  if (!process.env.BRIDGE_SIWE_JWT_SECRET || config.jwtSecret === "change-me-in-production") {
    throw new Error("Missing BRIDGE_SIWE_JWT_SECRET (refusing to start in production).");
  }
  if (config.requireRole && !config.roleContract) {
    throw new Error("BRIDGE_SIWE_REQUIRE_ROLE=1 requires BRIDGE_SIWE_ROLE_CONTRACT.");
  }
}

const app = express();
app.disable("x-powered-by");

app.use(
  helmet({
    // Keep CSP out of this service; frontend already sets CSP and this is an API.
    contentSecurityPolicy: false,
  }),
);

const allowedDomainSet = new Set((config.allowedDomains || []).map((d) => d.toLowerCase()));
const corsOrigin = (origin, cb) => {
  // Allow non-browser clients (no Origin header).
  if (!origin) return cb(null, true);
  try {
    const u = new URL(origin);
    const host = u.host.toLowerCase(); // includes port if present
    const hostname = u.hostname.toLowerCase();
    const ok = allowedDomainSet.has(host) || allowedDomainSet.has(hostname);
    return cb(ok ? null : new Error("CORS origin not allowed"), ok);
  } catch {
    return cb(new Error("Invalid Origin"), false);
  }
};

app.use(
  cors({
    origin: corsOrigin,
    credentials: true,
    methods: ["GET", "POST", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
    maxAge: 600,
  }),
);

// Validate inbound JSON: strict + size limits + parse error handling.
app.use(
  express.json({
    limit: process.env.BRIDGE_JSON_LIMIT || "1mb",
    strict: true,
    type: ["application/json", "application/*+json"],
  }),
);

app.use((err, _req, res, next) => {
  // Invalid JSON
  if (err instanceof SyntaxError && "body" in err) {
    return res.status(400).json({ ok: false, error: "invalid_json" });
  }
  return next(err);
});

const redis = new Redis(config.redisUrl, { maxRetriesPerRequest: 3 });
redis.on("error", (e) => console.warn("[redis]", e.message));

app.use(createAuthRouter(redis));

app.get("/health", (_, res) => {
  res.json({ ok: true, service: "bridge-auth" });
});

app.get("/", (_, res) => {
  res.json({
    service: "Bridge Auth",
    version: "1.0.0",
    endpoints: {
      auth_siwe: "POST /auth/siwe",
      auth_refresh: "POST /auth/refresh",
      auth_verify: "GET /auth/verify",
      ws_events: "WS /ws/events",
    },
    ladder: "QR → Wallet → Signature → Role Check → Session Token → Live Contract Sync",
  });
});

// Reject unknown routes.
app.use((_req, res) => res.status(404).json({ ok: false, error: "not_found" }));

// Last-resort error handler (avoid leaking internals).
app.use((err, _req, res, _next) => {
  console.error("[bridge-auth] error:", err?.message || err);
  res.status(500).json({ ok: false, error: "internal_error" });
});

const server = app.listen(config.port, () => {
  console.log(`Bridge Auth at http://localhost:${config.port}`);
});
attachWebSocket(server);
