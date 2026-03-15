# Deploy Checklist — Apply First Before Deploy

**Rule:** Apply the swarm scaling and topology docs **before** scaling or deploying to production. Do not leave or omit any of the 28 risks/fixes or the 5-layer topology when evolving the system.

---

## 1. Apply first (read and design against)

| Doc | Content |
|-----|--------|
| **[SWARM-SCALING-RISKS-AND-FIXES.md](./SWARM-SCALING-RISKS-AND-FIXES.md)** | **28 risks and fixes:** (1) Coordination overhead → hierarchical coordination. (2) Task routing bottlenecks → distributed task queues. (3) State sync → event logs, CRDT. (4) Node discovery explosion → gossip. (5) Identity → agent_id, node_id, lineage_id. (6) Duplicate work → task locks/claims. (7) Economic imbalance → UBI + reward balancing. (8) Agent specialization → skill specialization. (9) Resource scheduling → resource-aware. (10) Memory growth → archival + summarization. (11) Evolution drift → performance pruning. (12) Swarm fragmentation → cross-cluster routing. (13) Network latency → regional clusters. (14) Security → signed node registration. (15) Fault propagation → quarantine + rollback. (16) Feedback instability → replication rate caps. (17) Memory contamination → knowledge validation. (18) Task starvation → priority aging. (19) Economic inflation → supply control. (20) Skill discovery → skill registry. (21) Evolution tracking → lineage graph. (22) Observability → aggregated telemetry. (23) Deployment drift → version handshake. (24) Replication storms → replication throttling. (25) Market manipulation → reputation weighting. (26) Node churn → heartbeat monitoring. (27) Swarm governance → consensus voting. **(28) Global task bus** → task created → broadcast to swarm → best agent claims → execution → result returned. |
| **[SWARM-TOPOLOGY-5-LAYER.md](./SWARM-TOPOLOGY-5-LAYER.md)** | **5-layer topology:** Edge Agents (twins) → Local Clusters → Regional Coordinators → Global Orchestrators → Shared Knowledge Layer. Scaling rule: flat N² → hierarchical N×log N. Replication path: within cluster first, then regional, then global. Task flow: global task bus → regional router → cluster queue → agent execution. Example at 1M agents: 10k clusters, 200 regions, 10 global orchestrators. |
| **[SWARM-SCALE-UNLIMITED-5-TRICKS.md](./SWARM-SCALE-UNLIMITED-5-TRICKS.md)** | **Beyond ~1M agents — five tricks for unlimited scale:** (1) Fractal swarm — self-similar at every scale, cluster as super-agent. (2) Gossip-based knowledge propagation — O(log N), no central bottleneck. (3) Event stream architecture — events → distributed log, agents subscribe, event-driven. (4) Capability routing — task → capability index → best cluster → agent; skill-based. (5) Autonomous economic regulation — dynamic pricing, replication budgets, reputation; economics as governor. Bridge already has replication + economic layer. |

---

## 2. Target architecture (when 28th piece exists)

```
Infrastructure mesh
    ↓
Twin swarm
    ↓
Global task bus
    ↓
Marketplace economy
    ↓
Replication engine
    ↓
Evolution engine
    ↓
Digital ecosystem
```

---

## 3. What’s already in Bridge AI OS

- Replication engine  
- Node discovery (`/api/replication/status`, `/api/replication/nodes`, `/api/replication/register`)  
- Marketplace tasks  
- Twin evolution  

The **global task bus** (broadcast to swarm, best agent claims) is the usual final stabilizer before scaling to very large swarms.

---

## 4. Before you deploy

1. Read **SWARM-SCALING-RISKS-AND-FIXES.md** and **SWARM-TOPOLOGY-5-LAYER.md** (no omissions).  
2. For scale beyond ~1M agents, read **SWARM-SCALE-UNLIMITED-5-TRICKS.md** (fractal swarm, gossip, event streams, capability routing, economic regulation).  
3. Align design with the 28 fixes where applicable (identity, task claims, replication caps, gossip discovery, etc.).  
4. Plan for **global task bus** and **5-layer topology** when moving from ~1k to ~1M agents.  
5. Run tests: `pytest tests/test_api.py -v`.  
6. Run audit if available: `.\audit-wall.ps1`.  
7. Then run your deploy script (e.g. `.\run-full-install-build-deploy.ps1` or Cloudflare Worker deploy).

---

## References

- [GLOBAL-TWIN-SWARM-ARCHITECTURE.md](./GLOBAL-TWIN-SWARM-ARCHITECTURE.md)  
- [SELF-EXPANDING-AI-NETWORK.md](./SELF-EXPANDING-AI-NETWORK.md)  
- [REPO-STATE-AND-TARGET-ARCHITECTURE.md](./REPO-STATE-AND-TARGET-ARCHITECTURE.md)
