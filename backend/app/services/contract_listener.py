"""
Contract Event Listener — Marketplace activity on-chain.

Polls contract events (TaskCreated, TaskAccepted, etc.) and emits to internal systems.
Config: BRIDGE_CONTRACT_LISTENER=1, BRIDGE_CONTRACT_ADDRESS, BRIDGE_CONTRACT_RPC_URL
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

ENABLED = os.environ.get("BRIDGE_CONTRACT_LISTENER", "0") == "1"
CONTRACT_ADDRESS = os.environ.get("BRIDGE_CONTRACT_ADDRESS", "")
RPC_URL = os.environ.get("BRIDGE_CONTRACT_RPC_URL", "https://rpc.linea.build")
POLL_INTERVAL_SEC = int(os.environ.get("BRIDGE_CONTRACT_POLL_INTERVAL", "30"))

# Minimal ABI for common marketplace events
TASK_CREATED_TOPIC = "0x" + "0" * 64  # Placeholder; replace with actual event topic
TASK_ACCEPTED_TOPIC = "0x" + "0" * 64


async def run_listener(memory) -> None:
    """Background task: poll contract logs and persist/emit marketplace events."""
    if not ENABLED or not CONTRACT_ADDRESS:
        return
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not w3.is_connected():
            return
    except Exception:
        return

    last_block = 0
    while True:
        try:
            block = w3.eth.block_number
            if last_block == 0:
                last_block = max(0, block - 100)  # Initial: last 100 blocks
            if block <= last_block:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue
            logs = w3.eth.get_logs({
                "address": Web3.to_checksum_address(CONTRACT_ADDRESS),
                "fromBlock": last_block + 1,
                "toBlock": block,
            })
            for log in logs:
                await _process_log(memory, log)
            last_block = block
        except Exception:
            pass
        await asyncio.sleep(POLL_INTERVAL_SEC)


async def _process_log(memory, log) -> None:
    """Process event log: persist to Redis, emit to physics."""
    try:
        from app.physics import emit as physics_emit
        event = {
            "address": log.get("address"),
            "topics": [t.hex() if hasattr(t, "hex") else str(t) for t in (log.get("topics") or [])],
            "blockNumber": log.get("blockNumber"),
            "transactionHash": log.get("transactionHash").hex() if log.get("transactionHash") else None,
        }
        await memory.append("contract:events", event)
        physics_emit("contract_event", event)
    except Exception:
        pass
