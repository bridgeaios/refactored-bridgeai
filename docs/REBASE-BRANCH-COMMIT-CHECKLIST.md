# Rebase / Branch / Commit — Checklist

**Run this before rebase or branch commit to ensure the tree is ready.**

---

## 1. Run pipeline (recommended)

```powershell
.\run-debug-loop-learn-install-deploy-display.ps1 -SkipDeploy -SkipDisplay -ApproveStateOnce
```

This runs: **Debug** (state verify + pytest) → **Loop** (audit until 0 critical) → **Learn** (goals/tasks) → **Install** → **Deploy** (skipped) → **Display** (URLs only).

---

## 2. Approve state (if verify reported mutation)

After adding new files or changing tracked files, state verify may report "State mutation detected". Approve once so the manifest matches the current tree:

```powershell
node tools/state/verify.cjs --approve
```

Then run verify again to confirm clean:

```powershell
node tools/state/verify.cjs
```

(Exit code 0 = clean; exit code 2 = mutation, need approve.)

---

## 3. Quick checks before commit

| Check | Command | Expect |
|-------|---------|--------|
| State verify | `node tools/state/verify.cjs` | Exit 0 |
| Audit | `.\audit-wall.ps1` then check `audit-results.json` | criticalCount 0 |
| Tests | `$env:PYTHONPATH="e:\BridgeAI\BridgeLiveWall\backend"; python -m pytest tests/ -v` | 27 passed |

---

## 4. Rebase / branch / commit

- Create or switch to your branch; rebase on target (e.g. `main`) if needed.
- Stage and commit. The tree is ready when state verify passes, audit is 0 critical, and tests pass.

---

## 5. Optional: full run with log

For a full install → build → debug → deploy with log and goal=task:

```powershell
.\run-full-install-build-deploy.ps1 -SkipDeploy -ApproveStateOnce
```

Log: `logs/full-install-build-deploy.log`  
Goals: `data/goals-tasks.json` (`lastRun`).
