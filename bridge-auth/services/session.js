/** Session authority: short-lived JWT, refresh token with rotation. */
import jwt from "jsonwebtoken";
import { v4 as uuidv4 } from "uuid";
import config from "../config.js";

const REFRESH_PREFIX = "bridge:refresh:";
const SESSION_PREFIX = "bridge:session:";

export function createAccessToken(address, authority = "economic") {
  return jwt.sign(
    { sub: address, auth: authority, type: "access" },
    config.jwtSecret,
    { expiresIn: config.jwtExpirySec }
  );
}

export function createRefreshToken() {
  return uuidv4();
}

export function verifyAccessToken(token) {
  try {
    const payload = jwt.verify(token, config.jwtSecret);
    return payload.type === "access" ? payload : null;
  } catch {
    return null;
  }
}

export async function storeRefreshToken(redis, address, refreshToken) {
  const key = REFRESH_PREFIX + refreshToken;
  const val = JSON.stringify({ address, createdAt: Date.now() });
  await redis.setex(key, config.refreshExpirySec, val);
}

export async function consumeRefreshToken(redis, refreshToken) {
  const key = REFRESH_PREFIX + refreshToken;
  const val = await redis.get(key);
  if (!val) return null;
  await redis.del(key);
  return JSON.parse(val);
}

export function nonceKey(address, nonce) {
  return `siwe:nonce:${address}:${nonce}`;
}

export async function isNonceUsed(redis, address, nonce) {
  const key = nonceKey(address, nonce);
  return (await redis.get(key)) !== null;
}

export async function storeNonce(redis, address, nonce, ttlSec = 86400 * 7) {
  await redis.setex(nonceKey(address, nonce), ttlSec, "1");
}
