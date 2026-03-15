#!/usr/bin/env node
/**
 * BridgeLiveWall — automated ratification workflow
 *
 * One command to run after changes:
 * - Runs verifier to detect proposed root (prev -> next)
 * - If no change: exits 0
 * - If change:
 *   - If no quorum config: prints next root and instructs approve
 *   - If quorum config present:
 *       - checks signature file presence for nextRoot
 *       - if enough present, runs: verify.cjs --approve --require-quorum
 *       - otherwise prints missing signers + expected paths and exits 3
 */
/* eslint-disable no-console */
const fs = require("node:fs/promises");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const STATE_DIR = path.join(REPO_ROOT, ".bridge-state");
const QUORUM_PATH = path.join(STATE_DIR, "quorum.json");
const SIGS_DIR = path.join(STATE_DIR, "sigs");
const VERIFY = path.join(REPO_ROOT, "tools", "state", "verify.cjs");

function parseArgs(argv) {
  const args = {
    requireQuorum: true,
    approve: true,
    dryRun: false,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--no-quorum") args.requireQuorum = false;
    else if (a === "--dry-run") args.dryRun = true;
    else if (a === "--no-approve") args.approve = false;
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

function parsePrevNextFromOutput(text) {
  const okMatch = text.match(/State:\s*OK/i);
  if (okMatch) return { ok: true };

  // Avoid accidentally picking up "prev/next" from the per-file hash diff section.
  const marker = /State mutation detected\s*\(root mismatch\)\./i;
  const m = text.match(marker);
  if (!m || m.index == null) return { ok: false, parseError: true };
  const tail = text.slice(m.index);

  const prevMatch = tail.match(/^\s*prev:\s*([0-9a-f]{64})\s*$/im);
  const nextMatch = tail.match(/^\s*next:\s*([0-9a-f]{64})\s*$/im);
  if (!prevMatch || !nextMatch) return { ok: false, parseError: true };
  return { ok: false, prev: prevMatch[1], next: nextMatch[1] };
}

function runNode(scriptPath, args, opts = {}) {
  const r = spawnSync(process.execPath, [scriptPath, ...args], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    ...opts,
  });
  return {
    code: typeof r.status === "number" ? r.status : 1,
    stdout: r.stdout || "",
    stderr: r.stderr || "",
    combined: (r.stdout || "") + (r.stderr || ""),
  };
}

async function main() {
  const args = parseArgs(process.argv);

  // 1) Detect proposal (prev -> next).
  const detect = runNode(VERIFY, []);
  const parsed = parsePrevNextFromOutput(detect.combined);
  if (parsed.ok) {
    console.log("State: OK (no ratification needed).");
    process.exitCode = 0;
    return;
  }
  if (parsed.parseError) {
    console.error(detect.combined.trimEnd());
    console.error("");
    console.error("[ratify] Could not parse verifier output. Run `node tools/state/verify.cjs` directly.");
    process.exitCode = detect.code || 1;
    return;
  }

  const { prev, next } = parsed;
  console.log(`Proposed transition:\n  prev: ${prev}\n  next: ${next}\n`);

  // 2) Quorum present?
  const quorum = await readJsonIfExists(QUORUM_PATH);
  const hasQuorum = quorum && Array.isArray(quorum.keys) && quorum.keys.length > 0 && Number(quorum.threshold) >= 1;
  if (!hasQuorum || !args.requireQuorum) {
    console.log("No quorum enforcement (missing config or disabled).");
    console.log("To approve this transition:");
    console.log(`  node tools/state/verify.cjs --approve`);
    process.exitCode = 2;
    return;
  }

  const threshold = Number(quorum.threshold);
  const keyIds = quorum.keys.map((k) => String(k.id)).filter(Boolean).sort((a, b) => a.localeCompare(b, "en"));
  const sigDir = path.join(SIGS_DIR, next);

  // 3) Check which signature artifacts exist.
  const present = [];
  const missing = [];
  for (const id of keyIds) {
    const p = path.join(sigDir, `${id}.json`);
    try {
      await fs.access(p);
      present.push(id);
    } catch {
      missing.push(id);
    }
  }

  console.log(`Quorum required: need ${threshold} of ${keyIds.length}`);
  console.log(`Signatures present: ${present.length}`);

  if (present.length < threshold) {
    console.log("");
    console.log("Missing signatures:");
    for (const id of missing) console.log(`  - ${id}  (expects: .bridge-state/sigs/${next}/${id}.json)`);
    console.log("");
    console.log("Each signer runs (with THEIR private key):");
    console.log(`  node tools/state/sign.cjs --key ".bridge-state/keys/<their-keyId>.private.pem"`);
    console.log("");
    console.log("Then ratify:");
    console.log(`  node tools/state/ratify.cjs`);
    process.exitCode = 3;
    return;
  }

  if (args.dryRun || !args.approve) {
    console.log("");
    console.log("Dry-run: quorum artifacts present; would ratify via:");
    console.log("  node tools/state/verify.cjs --approve --require-quorum");
    process.exitCode = 0;
    return;
  }

  // 4) Attempt ratification (verifies signatures cryptographically).
  const ratify = runNode(VERIFY, ["--approve", "--require-quorum"]);
  process.stdout.write(ratify.stdout);
  process.stderr.write(ratify.stderr);
  process.exitCode = ratify.code;
}

main().catch((e) => {
  console.error("[ratify] fatal:", e && e.stack ? e.stack : e);
  process.exitCode = 1;
});

