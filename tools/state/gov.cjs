#!/usr/bin/env node
/**
 * BridgeLiveWall — governance amendments (key rotation / revocation)
 *
 * This operates on the authority set (quorum) and records amendments as
 * first-class ledger entries appended to: .bridge-state/roots.ndjson
 *
 * IMPORTANT:
 * - .bridge-state/ is excluded from the Merkle state hash by design.
 * - Governance can evolve without changing the application Merkle root.
 *
 * Workflow:
 * 1) Propose an amendment -> writes a proposal file under .bridge-state/gov/proposals/
 * 2) Council members sign the proposal payload offline -> .bridge-state/gov/sigs/<proposalId>/<keyId>.json
 * 3) Apply -> verifies quorum signatures, updates quorum.json, appends a gov entry to roots.ndjson
 */
/* eslint-disable no-console */
const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const STATE_DIR = path.join(REPO_ROOT, ".bridge-state");
const QUORUM_PATH = path.join(STATE_DIR, "quorum.json");
const ROOTS_LOG_PATH = path.join(STATE_DIR, "roots.ndjson");
const GOV_DIR = path.join(STATE_DIR, "gov");
const PROPOSALS_DIR = path.join(GOV_DIR, "proposals");
const GOV_SIGS_DIR = path.join(GOV_DIR, "sigs");

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function sha256(buf) {
  return crypto.createHash("sha256").update(buf).digest();
}

function stableStringify(value) {
  if (value === null || value === undefined) return "null";
  if (typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map((v) => stableStringify(v)).join(",") + "]";
  const keys = Object.keys(value).sort((a, b) => a.localeCompare(b.name ?? b, "en"));
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + stableStringify(value[k])).join(",") + "}";
}

function normalizePemNewlines(pem) {
  return String(pem).replace(/\r\n/g, "\n").trimEnd() + "\n";
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

async function readQuorum() {
  const cfg = (await readJsonIfExists(QUORUM_PATH)) || null;
  if (!cfg) throw new Error(`Missing quorum config at ${QUORUM_PATH}`);
  const threshold = Number(cfg.threshold);
  if (!Number.isFinite(threshold) || threshold < 1) throw new Error("Invalid quorum threshold.");
  if (!Array.isArray(cfg.keys) || cfg.keys.length === 0) throw new Error("Invalid quorum keys[].");
  const keys = cfg.keys.map((k) => ({
    id: String(k.id || "").trim(),
    alg: String(k.alg || "ed25519").toLowerCase(),
    publicKeyPem: normalizePemNewlines(k.publicKeyPem || ""),
    alias: k.alias ? String(k.alias) : undefined,
  }));
  for (const k of keys) {
    if (!k.id) throw new Error("Quorum key missing id.");
    if (k.alg !== "ed25519") throw new Error(`Unsupported alg ${k.alg}.`);
    if (!k.publicKeyPem.includes("BEGIN PUBLIC KEY")) throw new Error(`Key ${k.id} missing PEM publicKeyPem.`);
  }
  keys.sort((a, b) => a.id.localeCompare(b.id, "en"));
  if (threshold > keys.length) throw new Error("Threshold exceeds number of keys.");
  return { threshold, keys };
}

function quorumHash(quorum) {
  const payload = {
    threshold: quorum.threshold,
    keys: quorum.keys.map((k) => ({
      id: k.id,
      alg: k.alg,
      publicKeyPem: normalizePemNewlines(k.publicKeyPem),
      ...(k.alias ? { alias: k.alias } : {}),
    })),
  };
  return sha256Hex(Buffer.from(stableStringify(payload), "utf8"));
}

function deriveKeyIdFromPublicKeyPem(publicKeyPem) {
  const pub = crypto.createPublicKey(publicKeyPem);
  const spkiDer = pub.export({ type: "spki", format: "der" });
  const fp = sha256Hex(spkiDer);
  return { fingerprint: fp, keyId: `ed25519-${fp}` };
}

function governancePayload({ prevGovSha256, action, payloadObj }) {
  const lines = [
    "BridgeLiveWall Governance Approval v1",
    `prevGovSha256=${prevGovSha256}`,
    `action=${action}`,
    `payload=${stableStringify(payloadObj)}`,
  ];
  return Buffer.from(lines.join("\n") + "\n", "utf8");
}

function computeEntryHashStable(prevEntryHash, entryWithoutEntryHash) {
  const msg = (prevEntryHash || "") + "\n" + stableStringify(entryWithoutEntryHash) + "\n";
  return sha256Hex(Buffer.from(msg, "utf8"));
}

async function readLastNdjsonEntry(filePath) {
  try {
    const raw = await fs.readFile(filePath, "utf8");
    const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);
    if (lines.length === 0) return null;
    return JSON.parse(lines[lines.length - 1]);
  } catch (e) {
    if (e && e.code === "ENOENT") return null;
    throw e;
  }
}

async function appendRootsEntry(entry) {
  await fs.mkdir(STATE_DIR, { recursive: true });
  await fs.appendFile(ROOTS_LOG_PATH, JSON.stringify(entry) + "\n", "utf8");
}

async function anchorEntry(entry) {
  const url = (process.env.BRIDGE_STATE_ANCHOR_URL || "").trim();
  if (!url) return;
  const token = (process.env.BRIDGE_STATE_ANCHOR_TOKEN || "").trim();
  const headers = { "Content-Type": "application/json", "User-Agent": "BridgeLiveWall-Governance/1.0" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const failClosed = process.env.BRIDGE_STATE_ANCHOR_STRICT === "1";
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 5000);
    const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(entry), signal: ac.signal });
    clearTimeout(t);
    if (!res.ok) {
      const msg = `Anchor failed (${res.status} ${res.statusText})`;
      if (failClosed) throw new Error(msg);
      console.warn(`[gov] ${msg}`);
    }
  } catch (e) {
    const msg = `Anchor error: ${e?.message || e}`;
    if (failClosed) throw new Error(msg);
    console.warn(`[gov] ${msg}`);
  }
}

async function writeProposal(proposal) {
  await fs.mkdir(PROPOSALS_DIR, { recursive: true });
  const p = path.join(PROPOSALS_DIR, `${proposal.proposalId}.json`);
  await fs.writeFile(p, JSON.stringify(proposal, null, 2).replace(/\r\n/g, "\n") + "\n", "utf8");
  return p;
}

async function verifyGovSignatures({ quorum, proposal }) {
  const payload = Buffer.from(proposal.payloadBase64, "base64");
  const payloadSha256 = sha256Hex(payload);
  if (payloadSha256 !== proposal.payloadSha256) throw new Error("Proposal payload hash mismatch.");

  const dir = path.join(GOV_SIGS_DIR, proposal.proposalId);
  let files = [];
  try {
    const ents = await fs.readdir(dir, { withFileTypes: true });
    files = ents.filter((e) => e.isFile() && e.name.endsWith(".json")).map((e) => path.join(dir, e.name));
  } catch (e) {
    if (e.code !== "ENOENT") throw e;
  }
  files.sort((a, b) => a.localeCompare(b, "en"));

  const allowed = new Map(quorum.keys.map((k) => [k.id, k]));
  const approvedBy = [];

  for (const f of files) {
    let sig;
    try {
      sig = JSON.parse(await fs.readFile(f, "utf8"));
    } catch {
      continue;
    }
    const keyId = String(sig.keyId || "").trim();
    const sigBase64 = String(sig.sigBase64 || "").trim();
    const sigPayloadHash = String(sig.payloadSha256 || "").trim().toLowerCase();
    if (!allowed.has(keyId)) continue;
    if (!sigBase64) continue;
    if (sigPayloadHash && sigPayloadHash !== payloadSha256) continue;
    const key = allowed.get(keyId);
    const ok = crypto.verify(null, payload, key.publicKeyPem, Buffer.from(sigBase64, "base64"));
    if (ok) approvedBy.push(keyId);
  }

  // Unique + sorted
  const uniq = Array.from(new Set(approvedBy)).sort((a, b) => a.localeCompare(b, "en"));
  return { ok: uniq.length >= quorum.threshold, approvedBy: uniq, payloadSha256 };
}

async function applyAmendment({ proposal }) {
  const current = await readQuorum();
  const prevGovSha256 = quorumHash(current);
  if (proposal.prevGovSha256 !== prevGovSha256) {
    throw new Error(`prevGovSha256 mismatch. Current=${prevGovSha256} proposal=${proposal.prevGovSha256}`);
  }

  const sigCheck = await verifyGovSignatures({ quorum: current, proposal });
  if (!sigCheck.ok) {
    const dir = `.bridge-state/gov/sigs/${proposal.proposalId}/<keyId>.json`;
    const need = current.threshold;
    const have = sigCheck.approvedBy.length;
    const missing = current.keys.map((k) => k.id).filter((id) => !sigCheck.approvedBy.includes(id));
    console.log(`Quorum not satisfied: need ${need}, have ${have}`);
    console.log(`Proposal: ${proposal.proposalId}`);
    console.log(`Signatures dir: ${dir}`);
    console.log("Missing keyIds:");
    for (const m of missing) console.log(`  - ${m}`);
    process.exitCode = 3;
    return;
  }

  // Apply to produce next quorum
  const next = JSON.parse(JSON.stringify(current));
  if (proposal.action === "add_key") {
    const { id, alg, publicKeyPem, alias } = proposal.payload;
    if (next.keys.some((k) => k.id === id)) throw new Error(`Key already exists: ${id}`);
    next.keys.push({ id, alg, publicKeyPem: normalizePemNewlines(publicKeyPem), ...(alias ? { alias } : {}) });
    next.keys.sort((a, b) => a.id.localeCompare(b.id, "en"));
  } else if (proposal.action === "revoke_key") {
    const { keyId } = proposal.payload;
    next.keys = next.keys.filter((k) => k.id !== keyId);
    if (next.keys.length === 0) throw new Error("Cannot revoke last remaining key.");
    if (next.threshold > next.keys.length) next.threshold = next.keys.length;
  } else if (proposal.action === "set_threshold") {
    const { threshold } = proposal.payload;
    if (!Number.isFinite(threshold) || threshold < 1) throw new Error("Invalid threshold.");
    if (threshold > next.keys.length) throw new Error("Threshold exceeds key count.");
    next.threshold = threshold;
  } else {
    throw new Error(`Unknown action: ${proposal.action}`);
  }

  const nextGovSha256 = quorumHash(next);

  // Write quorum.json (source-of-truth for verify.cjs)
  await fs.mkdir(STATE_DIR, { recursive: true });
  await fs.writeFile(
    QUORUM_PATH,
    JSON.stringify({ threshold: next.threshold, keys: next.keys }, null, 2).replace(/\r\n/g, "\n") + "\n",
    "utf8",
  );

  // Append gov ledger entry to roots.ndjson
  const last = await readLastNdjsonEntry(ROOTS_LOG_PATH);
  const prevEntryHash = last?.entryHash || null;
  const ts = new Date().toISOString();

  const entryCore = {
    v: 2,
    entryAlg: "stablejson+prevEntryHash",
    ts,
    type: "gov",
    action: proposal.action,
    proposalId: proposal.proposalId,
    prevGovSha256,
    nextGovSha256,
    payloadSha256: sigCheck.payloadSha256,
    approvedBy: sigCheck.approvedBy,
    payload: proposal.payload,
    prevEntryHash,
  };
  const entryHash = computeEntryHashStable(prevEntryHash, entryCore);
  const entry = { ...entryCore, entryHash };

  await appendRootsEntry(entry);
  await anchorEntry(entry);

  console.log("Applied governance amendment.");
  console.log(`  action: ${proposal.action}`);
  console.log(`  proposalId: ${proposal.proposalId}`);
  console.log(`  prevGovSha256: ${prevGovSha256}`);
  console.log(`  nextGovSha256: ${nextGovSha256}`);
  console.log(`  approvedBy: ${sigCheck.approvedBy.join(", ")}`);
}

function usage() {
  console.log("Usage:");
  console.log("  node tools/state/gov.cjs status");
  console.log("  node tools/state/gov.cjs propose add-key --public <public.pem> [--alias <name>]");
  console.log("  node tools/state/gov.cjs propose revoke-key --key-id <keyId>");
  console.log("  node tools/state/gov.cjs propose set-threshold --threshold <n>");
  console.log("  node tools/state/gov.cjs apply --proposal <proposal.json>");
}

async function main() {
  const argv = process.argv.slice(2);
  const cmd = argv[0];
  if (!cmd) return usage();

  if (cmd === "status") {
    const q = await readQuorum();
    console.log(`threshold: ${q.threshold}`);
    console.log(`keys: ${q.keys.length}`);
    console.log(`govSha256: ${quorumHash(q)}`);
    for (const k of q.keys) console.log(`- ${k.id}${k.alias ? ` (${k.alias})` : ""}`);
    return;
  }

  if (cmd === "propose") {
    const sub = argv[1];
    const q = await readQuorum();
    const prevGovSha256 = quorumHash(q);

    if (sub === "add-key") {
      const pubIdx = argv.indexOf("--public");
      const aliasIdx = argv.indexOf("--alias");
      if (pubIdx < 0 || !argv[pubIdx + 1]) throw new Error("Missing --public <public.pem>");
      const publicKeyPem = normalizePemNewlines(await fs.readFile(path.resolve(argv[pubIdx + 1]), "utf8"));
      const alias = aliasIdx >= 0 && argv[aliasIdx + 1] ? String(argv[aliasIdx + 1]) : undefined;
      const derived = deriveKeyIdFromPublicKeyPem(publicKeyPem);
      const payload = { id: derived.keyId, alg: "ed25519", publicKeyPem, ...(alias ? { alias } : {}) };
      const payloadBuf = governancePayload({ prevGovSha256, action: "add_key", payloadObj: payload });
      const proposalId = sha256Hex(payloadBuf);
      const proposal = {
        v: 1,
        type: "gov_proposal",
        createdAt: new Date().toISOString(),
        action: "add_key",
        prevGovSha256,
        proposalId,
        payload,
        payloadSha256: sha256Hex(payloadBuf),
        payloadBase64: payloadBuf.toString("base64"),
      };
      const p = await writeProposal(proposal);
      console.log(`Wrote proposal: ${path.relative(REPO_ROOT, p)}`);
      console.log(`proposalId: ${proposalId}`);
      console.log(`Signatures dir: .bridge-state/gov/sigs/${proposalId}/<keyId>.json`);
      console.log("Each signer runs:");
      console.log(`  node tools/state/sign-gov.cjs --key ".bridge-state/keys/<their-keyId>.private.pem" --proposal "${path.relative(REPO_ROOT, p)}"`);
      console.log("Then apply:");
      console.log(`  node tools/state/gov.cjs apply --proposal "${path.relative(REPO_ROOT, p)}"`);
      return;
    }

    if (sub === "revoke-key") {
      const keyIdx = argv.indexOf("--key-id");
      if (keyIdx < 0 || !argv[keyIdx + 1]) throw new Error("Missing --key-id <keyId>");
      const keyId = String(argv[keyIdx + 1]).trim();
      const payload = { keyId };
      const payloadBuf = governancePayload({ prevGovSha256, action: "revoke_key", payloadObj: payload });
      const proposalId = sha256Hex(payloadBuf);
      const proposal = {
        v: 1,
        type: "gov_proposal",
        createdAt: new Date().toISOString(),
        action: "revoke_key",
        prevGovSha256,
        proposalId,
        payload,
        payloadSha256: sha256Hex(payloadBuf),
        payloadBase64: payloadBuf.toString("base64"),
      };
      const p = await writeProposal(proposal);
      console.log(`Wrote proposal: ${path.relative(REPO_ROOT, p)}`);
      console.log(`proposalId: ${proposalId}`);
      console.log(`Signatures dir: .bridge-state/gov/sigs/${proposalId}/<keyId>.json`);
      return;
    }

    if (sub === "set-threshold") {
      const tIdx = argv.indexOf("--threshold");
      if (tIdx < 0 || !argv[tIdx + 1]) throw new Error("Missing --threshold <n>");
      const threshold = parseInt(argv[tIdx + 1], 10);
      const payload = { threshold };
      const payloadBuf = governancePayload({ prevGovSha256, action: "set_threshold", payloadObj: payload });
      const proposalId = sha256Hex(payloadBuf);
      const proposal = {
        v: 1,
        type: "gov_proposal",
        createdAt: new Date().toISOString(),
        action: "set_threshold",
        prevGovSha256,
        proposalId,
        payload,
        payloadSha256: sha256Hex(payloadBuf),
        payloadBase64: payloadBuf.toString("base64"),
      };
      const p = await writeProposal(proposal);
      console.log(`Wrote proposal: ${path.relative(REPO_ROOT, p)}`);
      console.log(`proposalId: ${proposalId}`);
      console.log(`Signatures dir: .bridge-state/gov/sigs/${proposalId}/<keyId>.json`);
      return;
    }

    return usage();
  }

  if (cmd === "apply") {
    const pIdx = argv.indexOf("--proposal");
    if (pIdx < 0 || !argv[pIdx + 1]) throw new Error("Missing --proposal <proposal.json>");
    const proposalPath = path.resolve(argv[pIdx + 1]);
    const proposal = JSON.parse(await fs.readFile(proposalPath, "utf8"));
    await applyAmendment({ proposal });
    return;
  }

  return usage();
}

main().catch((e) => {
  console.error("[gov] fatal:", e && e.stack ? e.stack : e);
  process.exitCode = 1;
});

