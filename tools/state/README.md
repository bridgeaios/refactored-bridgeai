## Merkle state verification

This folder contains a deterministic, repo-wide state hasher used to detect (and localize) unauthorized mutations.

### What it does

- Hashes every file (SHA-256) under the repo root
- Excludes common build/vendor folders (`node_modules`, `dist`, `.git`, etc.)
- Sorts paths lexicographically (deterministic)
- Builds a Merkle tree and outputs a single **root hash**
- Writes/compares against an approved manifest at `.bridge-state/manifest.json`
- Logs a delta (added/removed/changed paths) when the root changes
- On approval (genesis or intentional mutation), appends a hash-chained entry to `.bridge-state/roots.ndjson`

### Run it

From repo root:

```bash
node tools/state/verify.cjs
```

### One-command workflow after changes

After you change code, run:

```bash
node tools/state/ratify.cjs
```

It will:

- detect the proposed `prev -> next` root transition
- if quorum is configured, check whether enough signature artifacts exist
- ratify automatically when ready (`--approve --require-quorum`)
- otherwise print exactly which signatures are missing and where to put them

### Approve a new root (intentional change)

```bash
node tools/state/verify.cjs --approve
```

Or via env:

```bash
BRIDGE_STATE_ALLOW_MUTATION=1 node tools/state/verify.cjs
```

### Enforcement (refuse deploy)

The verifier **fails the process** (exit code 2) when a root mismatch is detected and enforcement is active:

- `CI` is set, or
- `NODE_ENV=production`, or
- `BRIDGE_STATE_ENFORCE=1`

### External anchoring (publish roots outside the system)

If you set `BRIDGE_STATE_ANCHOR_URL`, each approved root appends to the local log **and** is POSTed as JSON to your endpoint.

- **BRIDGE_STATE_ANCHOR_URL**: destination webhook URL
- **BRIDGE_STATE_ANCHOR_TOKEN**: optional bearer token
- **BRIDGE_STATE_ANCHOR_STRICT=1**: fail the approval if anchoring fails (default is best-effort)

### Threshold governance (quorum signatures)

If `.bridge-state/quorum.json` exists (or `BRIDGE_STATE_QUORUM` is set), then in enforced environments (CI/production) **approvals require a quorum** of valid signatures.

Create `.bridge-state/quorum.json` like:

```json
{
  "threshold": 2,
  "keys": [
    { "id": "alice", "alg": "ed25519", "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n" },
    { "id": "bob",   "alg": "ed25519", "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n" },
    { "id": "carol", "alg": "ed25519", "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n" }
  ]
}
```

Signers generate signature artifacts offline:

```bash
node tools/state/sign.cjs --key "<path-to-private-key-pem>"
```

This writes:

- `.bridge-state/sigs/<nextRoot>/<keyId>.json`

Generate keys (and scaffold quorum config) with:

```bash
node tools/state/keygen.cjs --alias alice
node tools/state/keygen.cjs --alias bob
node tools/state/keygen.cjs --alias carol
```

By default, `keygen.cjs` writes private keys to your user profile folder:

- `%USERPROFILE%\\.bridge-keys\\BridgeLiveWall\\` (Windows)
- `~/.bridge-keys/BridgeLiveWall/` (macOS/Linux)

To write keys into the repo **(not recommended)**:

```bash
node tools/state/keygen.cjs --alias alice --in-repo
```

By default, key IDs are derived from key material:

- `keyId = "ed25519-" + sha256(publicKeySpkiDer)`

Then an approver can run:

```bash
node tools/state/verify.cjs --approve
```

To force quorum even outside CI/production:

- `node tools/state/verify.cjs --require-quorum`
- or set `BRIDGE_STATE_REQUIRE_QUORUM=1`

### Key rotation + revocation (governance ledger events)

Quorum membership/threshold can evolve without touching the Merkle state (because `.bridge-state/` is excluded).

- **Propose an amendment** (writes a proposal file):

```bash
node tools/state/gov.cjs propose add-key --public ".bridge-state/keys/<newKeyId>.public.pem" --alias "dave"
node tools/state/gov.cjs propose revoke-key --key-id "ed25519-<fingerprint>"
node tools/state/gov.cjs propose set-threshold --threshold 2
```

- **Council signs the proposal** (offline):

```bash
node tools/state/sign-gov.cjs --key "<path-to-private-key-pem>" --proposal ".bridge-state/gov/proposals/<proposalId>.json"
```

- **Apply the amendment** (verifies quorum signatures, updates `quorum.json`, appends a `type: "gov"` entry to `roots.ndjson`):

```bash
node tools/state/gov.cjs apply --proposal ".bridge-state/gov/proposals/<proposalId>.json"
```

