#!/usr/bin/env node
/**
 * BridgeLiveWall — Merkle state verifier
 *
 * Goals:
 * - Deterministically hash repo state (per-file SHA256 -> Merkle root).
 * - Compare against last known manifest root.
 * - Log delta (added/removed/changed).
 * - Refuse deploy/build when mutation is not explicitly authorized.
 *
 * Defaults:
 * - Enforce in CI or NODE_ENV=production, or when BRIDGE_STATE_ENFORCE=1.
 * - Allow approval via:
 *   - --approve
 *   - BRIDGE_STATE_ALLOW_MUTATION=1
 *   - BRIDGE_STATE_APPROVE_ROOT=<expected_new_root>
 *
 * Manifest location:
 *   <repoRoot>/.bridge-state/manifest.json
 */
/* eslint-disable no-console */
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const STATE_DIR = path.join(REPO_ROOT, ".bridge-state");
const MANIFEST_PATH = path.join(STATE_DIR, "manifest.json");
const ROOTS_LOG_PATH = path.join(STATE_DIR, "roots.ndjson");
const QUORUM_PATH = path.join(STATE_DIR, "quorum.json");
const SIGS_DIR = path.join(STATE_DIR, "sigs");

const DEFAULT_EXCLUDE_DIR_NAMES = new Set([
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
  "logs",  // run-full-install-build-deploy.ps1 writes here; exclude so pipeline doesn't flip Merkle root
]);

const DEFAULT_EXCLUDE_FILE_NAMES = new Set([
  ".DS_Store",
  "Thumbs.db",
  // Generated artifacts (audit + wallpaper) so normal runs don't cause root mismatch
  "audit-results.json",
  "twin_wall.png",
]);

function parseArgs(argv) {
  const args = {
    approve: false,
    baseDir: REPO_ROOT,
    manifestPath: MANIFEST_PATH,
    quiet: false,
    requireQuorum: false,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--approve") args.approve = true;
    else if (a === "--quiet") args.quiet = true;
    else if (a === "--require-quorum") args.requireQuorum = true;
    else if (a === "--base" && argv[i + 1]) args.baseDir = path.resolve(argv[++i]);
    else if (a === "--manifest" && argv[i + 1]) args.manifestPath = path.resolve(argv[++i]);
  }
  return args;
}

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function sha256(buf) {
  return crypto.createHash("sha256").update(buf).digest();
}

async function hashFileSha256Hex(filePath) {
  return await new Promise((resolve, reject) => {
    const h = crypto.createHash("sha256");
    const s = fs.createReadStream(filePath);
    s.on("error", reject);
    s.on("data", (chunk) => h.update(chunk));
    s.on("end", () => resolve(h.digest("hex")));
  });
}

function toRelPosix(baseDir, absPath) {
  const rel = path.relative(baseDir, absPath);
  // Deterministic path format in manifest / hashing.
  return rel.split(path.sep).join("/");
}

function shouldExcludeDir(dirName) {
  if (!dirName) return false;
  if (DEFAULT_EXCLUDE_DIR_NAMES.has(dirName)) return true;
  // common python/node artifacts
  if (dirName.endsWith(".egg-info")) return true;
  return false;
}

function shouldExcludeFile(fileName) {
  if (!fileName) return false;
  if (DEFAULT_EXCLUDE_FILE_NAMES.has(fileName)) return true;
  return false;
}

async function walkFiles(baseDir) {
  /** @type {string[]} */
  const out = [];
  async function walk(dir) {
    let entries = await fsp.readdir(dir, { withFileTypes: true });
    // Deterministic traversal.
    entries.sort((a, b) => a.name.localeCompare(b.name, "en"));
    for (const ent of entries) {
      const abs = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        if (shouldExcludeDir(ent.name)) continue;
        await walk(abs);
      } else if (ent.isFile()) {
        if (shouldExcludeFile(ent.name)) continue;
        out.push(abs);
      }
      // ignore symlinks and others for determinism & safety
    }
  }
  await walk(baseDir);
  // Deterministic file ordering.
  out.sort((a, b) => toRelPosix(baseDir, a).localeCompare(toRelPosix(baseDir, b), "en"));
  return out;
}

function leafHash(pathRelPosix, fileHashHex) {
  // Domain-separated leaf: sha256("leaf\0" + path + "\0" + fileHashHex)
  const msg = Buffer.from(`leaf\u0000${pathRelPosix}\u0000${fileHashHex}`, "utf8");
  return sha256(msg);
}

function parentHash(leftBuf, rightBuf) {
  // Domain-separated parent: sha256("node\0" + left + right)
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
      const right = layer[i + 1] ?? layer[i]; // duplicate last if odd
      next.push(parentHash(left, right));
    }
    layer = next;
  }
  return layer[0].toString("hex");
}

async function computeManifest(baseDir) {
  const absFiles = await walkFiles(baseDir);
  const files = [];
  const leaves = [];

  for (const abs of absFiles) {
    const rel = toRelPosix(baseDir, abs);
    const h = await hashFileSha256Hex(abs);
    files.push({ path: rel, sha256: h });
    leaves.push(leafHash(rel, h));
  }

  const root = merkleRootFromLeaves(leaves);
  return {
    version: 1,
    algorithm: {
      file: "sha256(bytes)",
      leaf: "sha256('leaf\\0' + pathPosix + '\\0' + fileSha256Hex)",
      node: "sha256('node\\0' + left + right) (duplicate last on odd layer)",
      root: "hex(sha256 tree)",
    },
    baseDir: path.resolve(baseDir),
    createdAt: new Date().toISOString(),
    fileCount: files.length,
    root,
    files,
  };
}

async function readJsonIfExists(p) {
  try {
    const raw = await fsp.readFile(p, "utf8");
    return JSON.parse(raw);
  } catch (e) {
    if (e && (e.code === "ENOENT" || e.code === "ENOTDIR")) return null;
    throw e;
  }
}

function indexByPath(files) {
  const m = new Map();
  for (const f of files || []) m.set(f.path, f.sha256);
  return m;
}

function computeDelta(prevManifest, nextManifest) {
  const prev = indexByPath(prevManifest?.files);
  const next = indexByPath(nextManifest?.files);

  const added = [];
  const removed = [];
  const changed = [];

  for (const [p, h] of next.entries()) {
    if (!prev.has(p)) added.push(p);
    else if (prev.get(p) !== h) changed.push(p);
  }
  for (const p of prev.keys()) {
    if (!next.has(p)) removed.push(p);
  }
  added.sort();
  removed.sort();
  changed.sort();
  return { added, removed, changed };
}

function isEnforced() {
  const env = process.env;
  if (env.BRIDGE_STATE_ENFORCE === "1") return true;
  if (env.BRIDGE_STATE_ENFORCE === "0") return false;
  if (env.CI && env.CI !== "0" && env.CI !== "false") return true;
  if ((env.NODE_ENV || "").toLowerCase() === "production") return true;
  return false;
}

async function ensureDir(p) {
  await fsp.mkdir(p, { recursive: true });
}

function stableStringify(value) {
  if (value === null || value === undefined) return "null";
  if (typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map((v) => stableStringify(v)).join(",") + "]";
  const keys = Object.keys(value).sort((a, b) => a.localeCompare(b, "en"));
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + stableStringify(value[k])).join(",") + "}";
}

function approvalPayload({ prevRoot, root, fileCount }) {
  // Stable, timestamp-independent payload to sign.
  const lines = [
    "BridgeLiveWall Root Approval v1",
    `prevRoot=${prevRoot || ""}`,
    `root=${root}`,
    `fileCount=${fileCount}`,
  ];
  return Buffer.from(lines.join("\n") + "\n", "utf8");
}

async function readQuorumConfig() {
  const env = process.env;
  const fromFile = await readJsonIfExists(QUORUM_PATH);
  if (fromFile) return fromFile;
  const raw = (env.BRIDGE_STATE_QUORUM || "").trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error("Invalid BRIDGE_STATE_QUORUM (must be JSON).");
  }
}

function normalizeQuorumConfig(cfg) {
  if (!cfg) return null;
  const threshold = Number(cfg.threshold);
  if (!Number.isFinite(threshold) || threshold < 1) throw new Error("Quorum threshold must be >= 1.");
  const keys = Array.isArray(cfg.keys) ? cfg.keys : [];
  if (keys.length === 0) throw new Error("Quorum config must include keys[].");
  const normalized = keys.map((k) => ({
    id: String(k.id || "").trim(),
    alg: (k.alg || "ed25519").toLowerCase(),
    publicKeyPem: String(k.publicKeyPem || "").trim(),
  }));
  for (const k of normalized) {
    if (!k.id) throw new Error("Quorum key is missing id.");
    if (k.alg !== "ed25519") throw new Error(`Unsupported quorum alg: ${k.alg} (only ed25519 supported).`);
    if (!k.publicKeyPem.includes("BEGIN PUBLIC KEY")) throw new Error(`Key ${k.id} publicKeyPem must be PEM.`);
  }
  if (threshold > normalized.length) throw new Error("Quorum threshold cannot exceed number of keys.");
  return { threshold, keys: normalized };
}

async function readSignatureFilesForRoot(root) {
  const dir = path.join(SIGS_DIR, root);
  try {
    const ents = await fsp.readdir(dir, { withFileTypes: true });
    const files = ents.filter((e) => e.isFile() && e.name.endsWith(".json")).map((e) => path.join(dir, e.name));
    files.sort((a, b) => a.localeCompare(b, "en"));
    const sigs = [];
    for (const p of files) {
      try {
        const raw = await fsp.readFile(p, "utf8");
        sigs.push({ path: p, data: JSON.parse(raw) });
      } catch (e) {
        sigs.push({ path: p, error: e?.message || String(e) });
      }
    }
    return sigs;
  } catch (e) {
    if (e && e.code === "ENOENT") return [];
    throw e;
  }
}

function verifyEd25519Signature(publicKeyPem, payloadBuf, signatureBase64) {
  const sig = Buffer.from(signatureBase64, "base64");
  return crypto.verify(null, payloadBuf, publicKeyPem, sig);
}

async function verifyQuorum({ quorum, prevRoot, nextRoot, fileCount, quiet }) {
  const payload = approvalPayload({ prevRoot, root: nextRoot, fileCount });
  const payloadSha256 = sha256Hex(payload);
  const sigFiles = await readSignatureFilesForRoot(nextRoot);

  /** @type {Map<string, {ok:boolean, reason?:string}>} */
  const resultsByKey = new Map();
  for (const k of quorum.keys) resultsByKey.set(k.id, { ok: false, reason: "missing_signature" });

  for (const s of sigFiles) {
    if (s.error) continue;
    const d = s.data || {};
    const keyId = String(d.keyId || "").trim();
    const alg = String(d.alg || "ed25519").toLowerCase();
    const sig = String(d.sigBase64 || "").trim();
    const claimedPayloadHash = String(d.payloadSha256 || "").trim().toLowerCase();
    if (!keyId || !resultsByKey.has(keyId)) continue;
    if (alg !== "ed25519") {
      resultsByKey.set(keyId, { ok: false, reason: `unsupported_alg:${alg}` });
      continue;
    }
    if (!sig) {
      resultsByKey.set(keyId, { ok: false, reason: "empty_signature" });
      continue;
    }
    if (claimedPayloadHash && claimedPayloadHash !== payloadSha256) {
      resultsByKey.set(keyId, { ok: false, reason: "payload_hash_mismatch" });
      continue;
    }
    const key = quorum.keys.find((x) => x.id === keyId);
    const ok = verifyEd25519Signature(key.publicKeyPem, payload, sig);
    resultsByKey.set(keyId, { ok, reason: ok ? undefined : "invalid_signature" });
  }

  const approvedBy = [];
  const failures = [];
  for (const [id, r] of resultsByKey.entries()) {
    if (r.ok) approvedBy.push(id);
    else failures.push({ id, reason: r.reason });
  }
  approvedBy.sort();

  if (!quiet) {
    console.log("");
    console.log(`Quorum: need ${quorum.threshold} of ${quorum.keys.length} signatures`);
    console.log(`Payload SHA256: ${payloadSha256}`);
    console.log(`Approved by: ${approvedBy.length ? approvedBy.join(", ") : "(none)"}`);
  }

  const ok = approvedBy.length >= quorum.threshold;
  return { ok, approvedBy, payloadSha256, failures };
}

async function readLastNdjsonEntry(filePath) {
  try {
    const raw = await fsp.readFile(filePath, "utf8");
    const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);
    if (lines.length === 0) return null;
    return JSON.parse(lines[lines.length - 1]);
  } catch (e) {
    if (e && e.code === "ENOENT") return null;
    throw e;
  }
}

function computeRootLogEntryHash(fields) {
  // Tamper-evident chain with forward-compatible hashing:
  // entryHash = sha256(prevEntryHash + "\n" + stable-json(entry-without-entryHash) + "\n")
  const { entryHash: _drop, ...rest } = fields;
  const msg = (fields.prevEntryHash || "") + "\n" + stableStringify(rest) + "\n";
  return sha256Hex(Buffer.from(msg, "utf8"));
}

async function appendRootLogEntry({ ts, root, prevRoot, fileCount, manifestSha256 }) {
  await ensureDir(STATE_DIR);
  const last = await readLastNdjsonEntry(ROOTS_LOG_PATH);
  const prevEntryHash = last?.entryHash || null;

  const entryFields = {
    v: 2,
    entryAlg: "stablejson+prevEntryHash",
    ts,
    root,
    prevRoot: prevRoot || null,
    fileCount,
    manifestSha256,
    prevEntryHash,
  };
  const entryHash = computeRootLogEntryHash(entryFields);
  const entry = { ...entryFields, entryHash };

  await fsp.appendFile(ROOTS_LOG_PATH, JSON.stringify(entry) + "\n", "utf8");
  return entry;
}

async function anchorEntry(entry) {
  const url = (process.env.BRIDGE_STATE_ANCHOR_URL || "").trim();
  if (!url) return;

  const token = (process.env.BRIDGE_STATE_ANCHOR_TOKEN || "").trim();
  const headers = { "Content-Type": "application/json", "User-Agent": "BridgeLiveWall-StateVerifier/1.0" };
  if (token) headers.Authorization = `Bearer ${token}`;

  // Best-effort, fail-closed only if explicitly requested.
  const failClosed = process.env.BRIDGE_STATE_ANCHOR_STRICT === "1";
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 5000);
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(entry),
      signal: ac.signal,
    });
    clearTimeout(t);
    if (!res.ok) {
      const msg = `Anchor failed (${res.status} ${res.statusText})`;
      if (failClosed) throw new Error(msg);
      console.warn(`[verify-state] ${msg}`);
    }
  } catch (e) {
    const msg = `Anchor error: ${e?.message || e}`;
    if (failClosed) throw new Error(msg);
    console.warn(`[verify-state] ${msg}`);
  }
}

async function writeManifest(p, manifest, { prevRoot, quorumEvidence } = {}) {
  await ensureDir(path.dirname(p));
  const tmp = `${p}.tmp`;
  const payload = JSON.stringify(manifest, null, 2) + "\n";
  await fsp.writeFile(tmp, payload, "utf8");
  await fsp.rename(tmp, p);

  // Append to the append-only log for every approved state transition.
  const manifestSha256 = sha256Hex(Buffer.from(payload, "utf8"));
  const entry = await appendRootLogEntry({
    ts: manifest.createdAt,
    root: manifest.root,
    prevRoot: prevRoot || null,
    fileCount: manifest.fileCount,
    manifestSha256,
  });
  if (quorumEvidence) {
    // Append an additional anchored event with quorum evidence by writing a second entry.
    // (We keep the manifest->root entry minimal and immutable; quorum evidence is optional metadata.)
    const meta = {
      v: 1,
      entryAlg: "meta",
      ts: manifest.createdAt,
      type: "quorum",
      root: manifest.root,
      prevRoot: prevRoot || null,
      quorum: quorumEvidence,
      prevEntryHash: entry.entryHash,
    };
    meta.entryHash = computeRootLogEntryHash(meta);
    await fsp.appendFile(ROOTS_LOG_PATH, JSON.stringify(meta) + "\n", "utf8");
    await anchorEntry(meta);
  }
  await anchorEntry(entry);
}

function printDelta(delta, prevManifest, nextManifest) {
  const maxList = 50;
  const { added, removed, changed } = delta;

  console.log("");
  console.log("State delta:");
  console.log(`  added:   ${added.length}`);
  console.log(`  removed: ${removed.length}`);
  console.log(`  changed: ${changed.length}`);

  const showList = (label, arr) => {
    if (arr.length === 0) return;
    console.log("");
    console.log(`${label} (showing up to ${maxList}):`);
    for (const p of arr.slice(0, maxList)) console.log(`  - ${p}`);
    if (arr.length > maxList) console.log(`  ... ${arr.length - maxList} more`);
  };

  showList("Added", added);
  showList("Removed", removed);
  showList("Changed", changed);

  // If changed is small, show hashes for quick diffing.
  if (changed.length > 0 && changed.length <= 20) {
    const prevIdx = indexByPath(prevManifest?.files);
    const nextIdx = indexByPath(nextManifest?.files);
    console.log("");
    console.log("Changed hashes:");
    for (const p of changed) {
      console.log(`  - ${p}`);
      console.log(`      prev: ${prevIdx.get(p)}`);
      console.log(`      next: ${nextIdx.get(p)}`);
    }
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const enforced = isEnforced();

  const prev = await readJsonIfExists(args.manifestPath);
  const next = await computeManifest(args.baseDir);

  if (!args.quiet) {
    console.log(`Merkle root: ${next.root}`);
    console.log(`Files: ${next.fileCount}`);
    console.log(`Base: ${path.resolve(args.baseDir)}`);
  }

  if (!prev) {
    // Genesis snapshot: create baseline manifest.
    await writeManifest(args.manifestPath, next, { prevRoot: null });
    if (!args.quiet) {
      console.log(`Genesis manifest written: ${path.relative(REPO_ROOT, args.manifestPath)}`);
      console.log(`Root log appended: ${path.relative(REPO_ROOT, ROOTS_LOG_PATH)}`);
    }
    return;
  }

  if (prev.root === next.root) {
    if (!args.quiet) console.log("State: OK (root matches approved manifest).");
    return;
  }

  const delta = computeDelta(prev, next);
  printDelta(delta, prev, next);

  const allowMutation = process.env.BRIDGE_STATE_ALLOW_MUTATION === "1";
  const approveRoot = (process.env.BRIDGE_STATE_APPROVE_ROOT || "").trim().toLowerCase();
  const approveByRoot = approveRoot && approveRoot === next.root.toLowerCase();
  const approving = args.approve || allowMutation || approveByRoot;

  if (approving) {
    const quorumCfgRaw = await readQuorumConfig();
    const quorumCfg = quorumCfgRaw ? normalizeQuorumConfig(quorumCfgRaw) : null;
    const requireQuorum = args.requireQuorum || process.env.BRIDGE_STATE_REQUIRE_QUORUM === "1";
    const quorumEnabled = !!quorumCfg && (requireQuorum || isEnforced());

    let quorumEvidence = null;
    if (quorumEnabled) {
      const qr = await verifyQuorum({
        quorum: quorumCfg,
        prevRoot: prev.root,
        nextRoot: next.root,
        fileCount: next.fileCount,
        quiet: args.quiet,
      });
      if (!qr.ok) {
        const msg =
          `Quorum approval required but not satisfied.\n` +
          `  need: ${quorumCfg.threshold} of ${quorumCfg.keys.length}\n` +
          `  have: ${qr.approvedBy.length}\n` +
          `  root: ${next.root}\n` +
          `\n` +
          `Signers should run:\n` +
          `  node tools/state/sign.cjs --key <private.pem>\n` +
          `\n` +
          `Signatures must be placed under:\n` +
          `  .bridge-state/sigs/${next.root}/<key-id>.json\n`;
        console.error("");
        console.error(msg);
        process.exitCode = 3;
        return;
      }
      quorumEvidence = {
        threshold: quorumCfg.threshold,
        approvedBy: qr.approvedBy,
        payloadSha256: qr.payloadSha256,
      };
    }

    await writeManifest(args.manifestPath, next, { prevRoot: prev.root, quorumEvidence });
    if (!args.quiet) {
      const why = args.approve ? "--approve" : allowMutation ? "BRIDGE_STATE_ALLOW_MUTATION=1" : "BRIDGE_STATE_APPROVE_ROOT matches";
      console.log("");
      console.log(`Approved new root (${why}). Manifest updated.`);
      console.log(`Root log appended: ${path.relative(REPO_ROOT, ROOTS_LOG_PATH)}`);
    }
    return;
  }

  const msg =
    `State mutation detected (root mismatch).\n` +
    `  prev: ${prev.root}\n` +
    `  next: ${next.root}\n` +
    `\n` +
    `To approve intentionally, rerun with one of:\n` +
    `  node tools/state/verify.cjs --approve\n` +
    `  BRIDGE_STATE_ALLOW_MUTATION=1 node tools/state/verify.cjs\n` +
    `  BRIDGE_STATE_APPROVE_ROOT=${next.root} node tools/state/verify.cjs\n`;

  if (enforced) {
    console.error("");
    console.error(msg);
    process.exitCode = 2;
    process.exit(2);
  }

  // Non-enforced: surface the anomaly and exit 2 so callers (e.g. run-full-loop.ps1) see failure.
  console.warn("");
  console.warn(msg);
  process.exit(2);
}

main().catch((e) => {
  console.error("[verify-state] fatal:", e && e.stack ? e.stack : e);
  process.exitCode = 1;
});

