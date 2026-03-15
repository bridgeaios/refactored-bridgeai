#!/usr/bin/env node
/**
 * BridgeLiveWall — quorum signer (ed25519)
 *
 * Produces a signature artifact for the current proposed state transition:
 *   prevRoot (from .bridge-state/manifest.json) -> nextRoot (computed)
 *
 * Output:
 *   .bridge-state/sigs/<nextRoot>/<keyId>.json
 *
 * Usage:
 *   node tools/state/sign.cjs --key .bridge-state/keys/<keyId>.private.pem
 *
 * You may pass --key-id, but by default it is derived from key material:
 *   keyId = "ed25519-" + sha256(publicKeySpkiDer)
 */
/* eslint-disable no-console */
const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const STATE_DIR = path.join(REPO_ROOT, ".bridge-state");
const MANIFEST_PATH = path.join(STATE_DIR, "manifest.json");
const SIGS_DIR = path.join(STATE_DIR, "sigs");

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function deriveKeyIdFromPrivateKeyPem(privateKeyPem) {
  const priv = crypto.createPrivateKey(privateKeyPem);
  const pub = crypto.createPublicKey(priv);
  const spkiDer = pub.export({ type: "spki", format: "der" });
  const fp = sha256Hex(spkiDer);
  return { fingerprint: fp, keyId: `ed25519-${fp}` };
}

function approvalPayload({ prevRoot, root, fileCount }) {
  const lines = [
    "BridgeLiveWall Root Approval v1",
    `prevRoot=${prevRoot || ""}`,
    `root=${root}`,
    `fileCount=${fileCount}`,
  ];
  return Buffer.from(lines.join("\n") + "\n", "utf8");
}

async function readJson(p) {
  const raw = await fs.readFile(p, "utf8");
  return JSON.parse(raw);
}

async function listFilesRecursive(baseDir, excludeNames) {
  const out = [];
  async function walk(dir) {
    const ents = await fs.readdir(dir, { withFileTypes: true });
    ents.sort((a, b) => a.name.localeCompare(b.name, "en"));
    for (const ent of ents) {
      const abs = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        if (excludeNames.has(ent.name)) continue;
        await walk(abs);
      } else if (ent.isFile()) {
        if (excludeNames.has(ent.name)) continue;
        out.push(abs);
      }
    }
  }
  await walk(baseDir);
  out.sort((a, b) => path.relative(baseDir, a).localeCompare(path.relative(baseDir, b), "en"));
  return out;
}

async function hashFileSha256Hex(filePath) {
  const h = crypto.createHash("sha256");
  const fh = await fs.open(filePath, "r");
  try {
    const stream = fh.createReadStream();
    await new Promise((resolve, reject) => {
      stream.on("data", (c) => h.update(c));
      stream.on("end", resolve);
      stream.on("error", reject);
    });
  } finally {
    await fh.close();
  }
  return h.digest("hex");
}

function toRelPosix(baseDir, absPath) {
  return path.relative(baseDir, absPath).split(path.sep).join("/");
}

function sha256(buf) {
  return crypto.createHash("sha256").update(buf).digest();
}

function leafHash(pathRelPosix, fileHashHex) {
  const msg = Buffer.from(`leaf\u0000${pathRelPosix}\u0000${fileHashHex}`, "utf8");
  return sha256(msg);
}

function parentHash(leftBuf, rightBuf) {
  const prefix = Buffer.from("node\u0000", "utf8");
  return sha256(Buffer.concat([prefix, leftBuf, rightBuf]));
}

function merkleRootFromLeaves(leafBuffers) {
  if (leafBuffers.length === 0) return sha256(Buffer.from("empty\u0000", "utf8")).toString("hex");
  let layer = leafBuffers.slice();
  while (layer.length > 1) {
    const next = [];
    for (let i = 0; i < layer.length; i += 2) {
      const left = layer[i];
      const right = layer[i + 1] ?? layer[i];
      next.push(parentHash(left, right));
    }
    layer = next;
  }
  return layer[0].toString("hex");
}

async function computeRoot(baseDir) {
  const exclude = new Set([
    ".git",
    ".hg",
    ".svn",
    ".bridge-state",
    ".cursor",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".vite",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    ".DS_Store",
    "Thumbs.db",
  ]);
  const filesAbs = await listFilesRecursive(baseDir, exclude);
  const leaves = [];
  for (const abs of filesAbs) {
    const rel = toRelPosix(baseDir, abs);
    const h = await hashFileSha256Hex(abs);
    leaves.push(leafHash(rel, h));
  }
  return { root: merkleRootFromLeaves(leaves), fileCount: filesAbs.length };
}

function parseArgs(argv) {
  const args = { keyPath: "", keyId: "", baseDir: REPO_ROOT };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--key" && argv[i + 1]) args.keyPath = argv[++i];
    else if (a === "--key-id" && argv[i + 1]) args.keyId = argv[++i];
    else if (a === "--base" && argv[i + 1]) args.baseDir = path.resolve(argv[++i]);
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.keyPath) {
    console.error("Usage: node tools/state/sign.cjs --key <private.pem> [--key-id <id>] [--base <repoRoot>]");
    process.exitCode = 2;
    return;
  }

  const prev = await readJson(MANIFEST_PATH);
  const { root: nextRoot, fileCount } = await computeRoot(args.baseDir);
  if (prev.root === nextRoot) {
    console.log("No-op: state root already matches manifest. Nothing to sign.");
    return;
  }

  const payload = approvalPayload({ prevRoot: prev.root, root: nextRoot, fileCount });
  const payloadSha256 = sha256Hex(payload);

  const privPem = await fs.readFile(path.resolve(args.keyPath), "utf8");
  const derived = deriveKeyIdFromPrivateKeyPem(privPem);
  const keyId = (args.keyId || derived.keyId).trim();
  const sig = crypto.sign(null, payload, privPem);
  const sigBase64 = sig.toString("base64");

  const outDir = path.join(SIGS_DIR, nextRoot);
  await fs.mkdir(outDir, { recursive: true });
  const outPath = path.join(outDir, `${keyId}.json`);
  const artifact = {
    keyId,
    alg: "ed25519",
    payloadSha256,
    sigBase64,
    signedAt: new Date().toISOString(),
    prevRoot: prev.root,
    root: nextRoot,
    fileCount,
    keyFingerprintSha256SpkiDer: derived.fingerprint,
  };
  await fs.writeFile(outPath, JSON.stringify(artifact, null, 2) + "\n", "utf8");

  console.log(`Signed payload SHA256: ${payloadSha256}`);
  console.log(`Root transition: ${prev.root} -> ${nextRoot}`);
  console.log(`Wrote signature: ${path.relative(REPO_ROOT, outPath)}`);
}

main().catch((e) => {
  console.error("[sign] fatal:", e && e.stack ? e.stack : e);
  process.exitCode = 1;
});

