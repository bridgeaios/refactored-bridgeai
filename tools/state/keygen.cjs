#!/usr/bin/env node
/**
 * BridgeLiveWall — quorum key generator (ed25519)
 *
 * Generates:
 * - private key PEM (PKCS8)
 * - public key PEM (SPKI)
 * - fingerprint = sha256(publicKeySpkiDer) hex
 * - keyId = "ed25519-" + fingerprint   (derived from key material; filename-safe)
 *
 * Optionally scaffolds/updates quorum config:
 *   .bridge-state/quorum.json
 *
 * Usage:
 *   node tools/state/keygen.cjs --alias alice
 *   node tools/state/keygen.cjs --alias bob --threshold 2
 *   node tools/state/keygen.cjs --no-quorum
 */
/* eslint-disable no-console */
const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const os = require("node:os");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const STATE_DIR = path.join(REPO_ROOT, ".bridge-state");
const DEFAULT_KEYS_DIR = path.join(os.homedir(), ".bridge-keys", "BridgeLiveWall");
const REPO_KEYS_DIR = path.join(STATE_DIR, "keys");
const QUORUM_PATH = path.join(STATE_DIR, "quorum.json");

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function deriveKeyIdFromPublicKey(publicKeyObj) {
  const spkiDer = publicKeyObj.export({ type: "spki", format: "der" });
  const fp = sha256Hex(spkiDer);
  return { fingerprint: fp, keyId: `ed25519-${fp}` };
}

function parseArgs(argv) {
  const args = {
    alias: "",
    threshold: 2,
    updateQuorum: true,
    force: false,
    inRepo: false,
    outDir: "",
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--alias" && argv[i + 1]) args.alias = argv[++i];
    else if (a === "--threshold" && argv[i + 1]) args.threshold = parseInt(argv[++i], 10);
    else if (a === "--no-quorum") args.updateQuorum = false;
    else if (a === "--force") args.force = true;
    else if (a === "--in-repo") args.inRepo = true;
    else if (a === "--out" && argv[i + 1]) args.outDir = argv[++i];
  }
  return args;
}

async function readJsonIfExists(p) {
  try {
    const raw = await fs.readFile(p, "utf8");
    return JSON.parse(raw);
  } catch (e) {
    if (e && e.code === "ENOENT") return null;
    throw e;
  }
}

async function writeFileNoClobber(filePath, data, force) {
  try {
    if (!force) {
      await fs.access(filePath);
      throw new Error(`Refusing to overwrite: ${filePath} (use --force)`);
    }
  } catch (e) {
    if (e && e.code !== "ENOENT") {
      // If access succeeded (file exists) and force was true, fall through to write.
      if (!force) throw e;
    }
  }
  await fs.writeFile(filePath, data, "utf8");
}

function normalizePemNewlines(pem) {
  // Deterministic formatting across platforms.
  return pem.replace(/\r\n/g, "\n").replace(/\n{3,}/g, "\n\n").trimEnd() + "\n";
}

function sortKeysForQuorum(keys) {
  return keys.slice().sort((a, b) => String(a.id).localeCompare(String(b.id), "en"));
}

async function upsertQuorumKey({ threshold, keyId, publicKeyPem, alias }) {
  await fs.mkdir(STATE_DIR, { recursive: true });

  const existing = (await readJsonIfExists(QUORUM_PATH)) || { threshold, keys: [] };
  if (!Number.isFinite(existing.threshold) || existing.threshold < 1) existing.threshold = threshold;
  if (!Array.isArray(existing.keys)) existing.keys = [];

  // Keep threshold sane.
  if (!Number.isFinite(threshold) || threshold < 1) threshold = 2;
  if (existing.keys.length === 0) existing.threshold = threshold;

  const idx = existing.keys.findIndex((k) => String(k.id) === keyId);
  const entry = {
    id: keyId,
    alg: "ed25519",
    publicKeyPem,
    ...(alias ? { alias } : {}),
  };
  if (idx >= 0) existing.keys[idx] = { ...existing.keys[idx], ...entry };
  else existing.keys.push(entry);

  existing.keys = sortKeysForQuorum(existing.keys);
  if (existing.threshold > existing.keys.length) existing.threshold = Math.max(1, existing.keys.length);

  const payload = JSON.stringify(existing, null, 2).replace(/\r\n/g, "\n") + "\n";
  await fs.writeFile(QUORUM_PATH, payload, "utf8");
}

async function main() {
  const args = parseArgs(process.argv);
  if (!Number.isFinite(args.threshold) || args.threshold < 1) {
    console.error("Invalid --threshold (must be >= 1).");
    process.exitCode = 2;
    return;
  }

  const keysDir = path.resolve(args.outDir || (args.inRepo ? REPO_KEYS_DIR : DEFAULT_KEYS_DIR));
  await fs.mkdir(keysDir, { recursive: true });

  const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
  const { fingerprint, keyId } = deriveKeyIdFromPublicKey(publicKey);

  const privPem = normalizePemNewlines(privateKey.export({ type: "pkcs8", format: "pem" }));
  const pubPem = normalizePemNewlines(publicKey.export({ type: "spki", format: "pem" }));

  const privPath = path.join(keysDir, `${keyId}.private.pem`);
  const pubPath = path.join(keysDir, `${keyId}.public.pem`);
  const metaPath = path.join(keysDir, `${keyId}.json`);

  await writeFileNoClobber(privPath, privPem, args.force);
  await writeFileNoClobber(pubPath, pubPem, args.force);

  const meta = {
    v: 1,
    alg: "ed25519",
    keyId,
    fingerprintSha256SpkiDer: fingerprint,
    alias: args.alias || null,
    createdAt: new Date().toISOString(),
    files: {
      privateKeyPem: path.relative(REPO_ROOT, privPath).replace(/\\/g, "/"),
      publicKeyPem: path.relative(REPO_ROOT, pubPath).replace(/\\/g, "/"),
    },
  };
  await writeFileNoClobber(metaPath, JSON.stringify(meta, null, 2).replace(/\r\n/g, "\n") + "\n", args.force);

  if (args.updateQuorum) {
    await upsertQuorumKey({ threshold: args.threshold, keyId, publicKeyPem: pubPem, alias: args.alias || "" });
  }

  console.log(`Generated ed25519 key pair`);
  console.log(`  keyId:       ${keyId}`);
  console.log(`  fingerprint: ${fingerprint}`);
  console.log(`  private:     ${privPath}`);
  console.log(`  public:      ${pubPath}`);
  console.log(`  meta:        ${metaPath}`);
  if (args.updateQuorum) console.log(`  quorum:      ${path.relative(REPO_ROOT, QUORUM_PATH)}`);
}

main().catch((e) => {
  console.error("[keygen] fatal:", e && e.stack ? e.stack : e);
  process.exitCode = 1;
});

