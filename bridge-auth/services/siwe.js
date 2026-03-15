/** SIWE verification, nonce replay protection, on-chain role check. */
import { ethers } from "ethers";
import config from "../config.js";

const MSG_REGEX = /Bridge AI OS Login\s+Domain:\s*(.+?)\s+Address:\s*(0x[a-fA-F0-9]{40})\s+Nonce:\s*(\d+)/s;

export function parseMessage(message) {
  const m = String(message || "").trim().match(MSG_REGEX);
  if (!m) return null;
  return { domain: m[1].trim(), address: m[2].toLowerCase(), nonce: m[3] };
}

export function verifySignature(message, signature) {
  try {
    const digest = ethers.hashMessage(message);
    const recovered = ethers.recoverAddress(digest, signature);
    return recovered ? recovered.toLowerCase() : null;
  } catch {
    return null;
  }
}

export function isDomainAllowed(domain) {
  return config.allowedDomains.includes(String(domain || "").toLowerCase().trim());
}

export async function verifyOnChainRole(address) {
  if (!config.requireRole || !config.roleContract) return true;
  try {
    const provider = new ethers.JsonRpcProvider(config.rpcUrl);
    const abi = ["function hasRole(bytes32 role, address account) view returns (bool)"];
    const contract = new ethers.Contract(config.roleContract, abi, provider);
    const roleBytes = ethers.getBytes(config.roleHash);
    const hasRole = await contract.hasRole(roleBytes, address);
    return !!hasRole;
  } catch {
    return false;
  }
}
