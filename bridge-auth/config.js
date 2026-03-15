/** Bridge Auth — Identity & Authority Layer. Production config. */
export default {
  port: parseInt(process.env.BRIDGE_AUTH_PORT || "3030", 10),
  redisUrl: process.env.REDIS_URL || "redis://localhost:6379/1",
  jwtSecret: process.env.BRIDGE_SIWE_JWT_SECRET || "change-me-in-production",
  jwtExpirySec: parseInt(process.env.BRIDGE_JWT_EXPIRY || "900", 10),       // 15 min
  refreshExpirySec: parseInt(process.env.BRIDGE_REFRESH_EXPIRY || "604800", 10), // 7 days
  allowedDomains: (process.env.BRIDGE_SIWE_ALLOWED_DOMAINS || "localhost,localhost:3020,localhost:3030,127.0.0.1")
    .split(",").map(d => d.trim().toLowerCase()).filter(Boolean),
  rpcUrl: process.env.BRIDGE_SIWE_RPC_URL || "https://rpc.linea.build",
  chainId: parseInt(process.env.BRIDGE_SIWE_CHAIN_ID || "59144", 10),
  roleContract: process.env.BRIDGE_SIWE_ROLE_CONTRACT || "",
  roleHash: process.env.BRIDGE_SIWE_ROLE_HASH || "0x0000000000000000000000000000000000000000000000000000000000000000",
  requireRole: process.env.BRIDGE_SIWE_REQUIRE_ROLE === "1",
  contractAddress: process.env.BRIDGE_CONTRACT_ADDRESS || "",
  contractPollIntervalSec: parseInt(process.env.BRIDGE_CONTRACT_POLL_INTERVAL || "15", 10),
};
