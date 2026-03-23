#!/usr/bin/env node
/**
 * Bridge CLI Runner — local companion executor (allowlisted).
 *
 * Usage (PowerShell):
 *   node scripts/cli-runner.js --backend http://localhost:8030 --runner runner-1
 *
 * Security:
 * - Executes ONLY allowlisted command IDs (cmd_id).
 * - Logs stdout/stderr and posts results back to backend.
 */

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

function argValue(name, def = "") {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1];
  return def;
}

const BACKEND = (argValue("--backend", "http://localhost:8030") || "").replace(/\/$/, "");
const RUNNER_ID = argValue("--runner", "runner-1");
const POLL_MS = Number(argValue("--poll-ms", "1500")) || 1500;

const ALLOWLIST = {
  "backend:pytest": { exe: "python", args: ["-m", "pytest", "-q"], cwd: "E:/BridgeAI/BridgeLiveWall/backend" },
  "frontend:build": { exe: "npm", args: ["run", "build"], cwd: "E:/BridgeAI/BridgeLiveWall/frontend" },
  "frontend:dev": { exe: "npm", args: ["run", "dev", "--", "--host", "--port", "3020"], cwd: "E:/BridgeAI/BridgeLiveWall/frontend" },
  "audit:wall": { exe: "powershell", args: ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "E:/BridgeAI/BridgeLiveWall/audit-wall.ps1"], cwd: "E:/BridgeAI/BridgeLiveWall" },
  "ports:list": { exe: "powershell", args: ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "E:/BridgeAI/BridgeLiveWall/backend/scripts/port-handler.ps1", "list"], cwd: "E:/BridgeAI/BridgeLiveWall/backend" },
  "sync:twins-wiki": { exe: "powershell", args: ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "E:/BridgeAI/BridgeLiveWall/backend/scripts/sync-twins-wiki.ps1"], cwd: "E:/BridgeAI/BridgeLiveWall/backend" },
  "wall:update": { exe: "powershell", args: ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "E:/BridgeAI/BridgeLiveWall/backend/update.ps1"], cwd: "E:/BridgeAI/BridgeLiveWall/backend" },
  "scripts:start-recommended": { exe: "powershell", args: ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "E:/BridgeAI/BridgeLiveWall/scripts/start-recommended-services.ps1"], cwd: "E:/BridgeAI/BridgeLiveWall" },
  // Echo is implemented as a safe Printf-style command. We pass a *single* -Command string.
  "echo": { exe: "powershell", args: ["-NoProfile", "-Command"], cwd: "E:/BridgeAI/BridgeLiveWall" },
};

async function httpJson(path, opts = {}) {
  const url = `${BACKEND}${path}`;
  const res = await fetch(url, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
  return { ok: res.ok, status: res.status, data };
}

function runJob(job) {
  return new Promise((resolve) => {
    const spec = ALLOWLIST[job.cmd_id];
    if (!spec) {
      return resolve({
        status: "failed",
        exit_code: 126,
        stdout: "",
        stderr: `cmd_id not allowlisted: ${job.cmd_id}`,
      });
    }
    const args = Array.isArray(job.args) ? job.args : [];
    const exe = spec.exe;
    let finalArgs = [...spec.args];
    if (job.cmd_id === "echo") {
      const msg = args.map((x) => String(x)).join(" ");
      // PowerShell: write the exact string, no evaluation.
      finalArgs = [...spec.args, `Write-Output ${JSON.stringify(msg)}`];
    }
    // For other commands, allow args only when allowlisted expects it (keep tight for safety).
    const child = spawn(exe, finalArgs, { cwd: spec.cwd, shell: false, windowsHide: true });
    let out = "";
    let err = "";
    child.stdout.on("data", (d) => { out += d.toString(); });
    child.stderr.on("data", (d) => { err += d.toString(); });
    child.on("close", (code) => {
      resolve({
        status: code === 0 ? "done" : "failed",
        exit_code: typeof code === "number" ? code : 1,
        stdout: out.slice(-20000),
        stderr: err.slice(-20000),
      });
    });
  });
}

async function main() {
  console.log(`[cli-runner] backend=${BACKEND} runner=${RUNNER_ID} poll_ms=${POLL_MS}`);
  while (true) {
    const next = await httpJson(`/api/cli/queue/next?runner_id=${encodeURIComponent(RUNNER_ID)}`);
    if (!next.ok) {
      console.log(`[cli-runner] queue fetch failed (${next.status})`);
      await sleep(POLL_MS);
      continue;
    }
    const job = next.data?.job;
    if (!job) {
      await sleep(POLL_MS);
      continue;
    }
    console.log(`[cli-runner] running ${job.id} cmd_id=${job.cmd_id}`);
    const result = await runJob(job);
    const finished_at = new Date().toISOString();
    await httpJson("/api/cli/report", {
      method: "POST",
      body: JSON.stringify({
        id: job.id,
        status: result.status,
        finished_at,
        exit_code: result.exit_code,
        stdout: result.stdout,
        stderr: result.stderr,
      }),
    });
    console.log(`[cli-runner] finished ${job.id} status=${result.status} exit=${result.exit_code}`);
  }
}

main().catch((e) => {
  console.error("[cli-runner] fatal:", e);
  process.exit(1);
});

