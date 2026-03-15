/** Real-time contract event monitoring. Polls RPC, pushes to WebSocket clients. */
import { ethers } from "ethers";
import config from "../config.js";

let lastBlock = 0n;
let provider = null;

export function getProvider() {
  if (!provider) provider = new ethers.JsonRpcProvider(config.rpcUrl);
  return provider;
}

export async function* pollEvents() {
  if (!config.contractAddress) return;
  const p = getProvider();
  const connected = await p.getBlockNumber().catch(() => null);
  if (connected === null) return;

  if (lastBlock === 0n) lastBlock = BigInt(Math.max(0, Number(connected) - 100));

  while (true) {
    try {
      const block = await p.getBlockNumber();
      if (block <= lastBlock) {
        await sleep(config.contractPollIntervalSec * 1000);
        continue;
      }
      const logs = await p.getLogs({
        address: config.contractAddress,
        fromBlock: lastBlock + 1n,
        toBlock: block,
      });
      for (const log of logs) {
        yield {
          address: log.address,
          topics: (log.topics || []).map(t => (typeof t === "string" ? t : t?.hex?.() ?? String(t))),
          blockNumber: Number(log.blockNumber),
          transactionHash: log.transactionHash,
        };
      }
      lastBlock = block;
    } catch (e) {
      console.warn("[contractWatcher]", e.message);
    }
    await sleep(config.contractPollIntervalSec * 1000);
  }
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
