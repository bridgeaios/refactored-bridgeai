/** Auth routes: SIWE login, refresh. */
import { Router } from "express";
import * as siwe from "../services/siwe.js";
import * as session from "../services/session.js";

export function createAuthRouter(redis) {
  const router = Router();

  router.post("/auth/siwe", async (req, res) => {
    try {
      const { message, signature } = req.body || {};
      if (!message || !signature) {
        return res.status(400).json({ error: "message and signature required" });
      }

      const parsed = siwe.parseMessage(message);
      if (!parsed) {
        return res.status(400).json({ error: "invalid message format" });
      }

      const { domain, address, nonce } = parsed;
      if (!siwe.isDomainAllowed(domain)) {
        return res.status(403).json({ error: "domain not allowed" });
      }

      const recovered = siwe.verifySignature(message, signature);
      if (!recovered || recovered !== address) {
        return res.status(401).json({ error: "signature verification failed" });
      }

      if (await session.isNonceUsed(redis, address, nonce)) {
        return res.status(401).json({ error: "nonce already used (replay)" });
      }

      if (!(await siwe.verifyOnChainRole(address))) {
        return res.status(403).json({ error: "on-chain role verification failed" });
      }

      await session.storeNonce(redis, address, nonce);

      const accessToken = session.createAccessToken(address);
      const refreshToken = session.createRefreshToken();
      await session.storeRefreshToken(redis, address, refreshToken);

      return res.json({
        ok: true,
        data: {
          token: accessToken,
          refreshToken,
          address,
          auth: "economic",
          expiresIn: 900,
        },
      });
    } catch (e) {
      console.error("[auth/siwe]", e);
      return res.status(500).json({ error: "internal error" });
    }
  });

  router.post("/auth/refresh", async (req, res) => {
    try {
      const { refreshToken } = req.body || {};
      if (!refreshToken) {
        return res.status(400).json({ error: "refreshToken required" });
      }

      const data = await session.consumeRefreshToken(redis, refreshToken);
      if (!data) {
        return res.status(401).json({ error: "invalid or expired refresh token" });
      }

      const accessToken = session.createAccessToken(data.address);
      const newRefreshToken = session.createRefreshToken();
      await session.storeRefreshToken(redis, data.address, newRefreshToken);

      return res.json({
        ok: true,
        data: {
          token: accessToken,
          refreshToken: newRefreshToken,
          address: data.address,
          auth: "economic",
          expiresIn: 900,
        },
      });
    } catch (e) {
      console.error("[auth/refresh]", e);
      return res.status(500).json({ error: "internal error" });
    }
  });

  router.get("/auth/verify", (req, res) => {
    const auth = req.headers.authorization?.replace(/^Bearer\s+/i, "") || req.query?.token;
    if (!auth) {
      return res.status(401).json({ valid: false });
    }
    const payload = session.verifyAccessToken(auth);
    if (!payload) {
      return res.status(401).json({ valid: false });
    }
    return res.json({ valid: true, address: payload.sub, auth: payload.auth });
  });

  return router;
}
