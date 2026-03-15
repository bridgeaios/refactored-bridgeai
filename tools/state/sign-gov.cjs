#!/usr/bin/env node
/**
 * BridgeLiveWall — governance proposal signer (ed25519)
 *
 * Signs a governance proposal produced by tools/state/gov.cjs
 *
 * Usage:
 *   node tools/state/sign-gov.cjs --key .bridge-state/keys/<keyId>.private.pem --proposal .bridge-state/gov/proposals/<proposalId>.json
 *
 * Output:
 *   .bridge-state/gov/sigs/<proposalId>/<keyId>.json
 */
/* eslint-disable no-console */
const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const GOV_SIGS_DIR = path.join(REPO_ROOT, ".bridge-state", "gov", "sigs");

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

function parseArgs(argv) {
  const args = { keyPath: "", proposalPath: "" };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--key" && argv[i + 1]) args.keyPath = argv[++i];
    else if (a === "--proposal" && argv[i + 1]) args.proposalPath = argv[++i];
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.keyPath || !args.proposalPath) {
    console.error("Usage: node tools/state/sign-gov.cjs --key <private.pem> --proposal <proposal.json>");
    process.exitCode = 2;
    return;
  }

  const proposal = JSON.parse(await fs.readFile(path.resolve(args.proposalPath), "utf8"));
  if (!proposal || proposal.type !== "gov_proposal" || !proposal.payloadBase64 || !proposal.proposalId) {
    throw new Error("Invalid proposal file.");
  }
  const payload = Buffer.from(proposal.payloadBase64, "base64");
  const payloadSha256 = sha256Hex(payload);
  if (payloadSha256 !== proposal.payloadSha256) throw new Error("Proposal payload hash mismatch.");
  if (proposal.proposalId !== sha256Hex(payload)) throw new Error("ProposalId mismatch (expected sha256(payload)).");

  const privPem = await fs.readFile(path.resolve(args.keyPath), "utf8");
  const derived = deriveKeyIdFromPrivateKeyPem(privPem);
  const keyId = derived.keyId;

  const sig = crypto.sign(null, payload, privPem);
  const sigBase64 = sig.toString("base64");

  const outDir = path.join(GOV_SIGS_DIR, proposal.proposalId);
  await fs.mkdir(outDir, { recursive: true });
  const outPath = path.join(outDir, `${keyId}.json`);
  const artifact = {
    keyId,
    alg: "ed25519",
    payloadSha256,
    sigBase64,
    signedAt: new Date().toISOString(),
    proposalId: proposal.proposalId,
    action: proposal.action,
    keyFingerprintSha256SpkiDer: derived.fingerprint,
  };
  await fs.writeFile(outPath, JSON.stringify(artifact, null, 2).replace(/\r\n/g, "\n") + "\n", "utf8");

  console.log(`Signed governance payload SHA256: ${payloadSha256}`);
  console.log(`proposalId: ${proposal.proposalId}`);
  console.log(`Wrote signature: ${path.relative(REPO_ROOT, outPath)}`);
}

main().catch((e) => {
  console.error("[sign-gov] fatal:", e && e.stack ? e.stack : e);
  process.exitCode = 1;
});

