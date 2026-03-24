"""
Swarm Message Bus - Redis-based inter-agent communication.

Channels:
- swarm:broadcast - Global announcements
- agent:{id}:tasks - Individual task queues
- agent:{id}:events - Event subscriptions
- mission:{id}:updates - Mission progress
- skill:share - Knowledge transfer
"""
import json
import logging
from datetime import datetime
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentEvent(str, Enum):
    """Event types for agent communication."""
    TASK_COMPLETED = "task.completed"
    SKILL_LEARNED = "skill.learned"
    DRIFT_DETECTED = "drift.detected"
    MISSION_ASSIGNED = "mission.assigned"
    MISSION_COMPLETED = "mission.completed"
    COLLABORATION_REQUESTED = "collaboration.requested"
    HEARTBEAT = "agent.heartbeat"
    STATE_SYNC = "agent.state_sync"


class AgentMessage(BaseModel):
    """Message structure for agent communication."""
    sender_id: str
    recipient_id: str | None = None
    channel: str
    payload: dict
    correlation_id: str
    timestamp: datetime
    event_type: AgentEvent | None = None


class SwarmMessageBus:
    """Redis-based message bus for swarm communication."""

    CHANNELS: dict[str, str] = {  # noqa: RUF012
        "broadcast": "swarm:broadcast",
        "tasks": "agent:{id}:tasks",
        "events": "agent:{id}:events",
        "mission_updates": "mission:{id}:updates",
        "skill_share": "skill:share",
    }

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._client: redis.Redis | None = None
        self._pubsub = None

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            await self._client.ping()
            logger.info(f"Swarm message bus connected to {self.redis_url}")
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}")
            self._client = None

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._pubsub:
            await self._pubsub.close()
        if self._client:
            await self._client.close()
        logger.info("Swarm message bus disconnected")

    async def publish(
        self,
        channel: str,
        message: AgentMessage,
    ) -> int:
        """Publish message to channel."""
        if not self._client:
            return 0
        msg_json = json.dumps(message.model_dump(), default=str)
        return await self._client.publish(channel, msg_json)

    async def publish_broadcast(self, message: AgentMessage) -> int:
        """Publish to broadcast channel."""
        return await self.publish(self.CHANNELS["broadcast"], message)

    async def publish_to_agent(
        self,
        agent_id: str,
        message: AgentMessage,
    ) -> int:
        """Publish to specific agent's task channel."""
        channel = self.CHANNELS["tasks"].format(id=agent_id)
        return await self.publish(channel, message)

    async def publish_agent_event(
        self,
        agent_id: str,
        message: AgentMessage,
    ) -> int:
        """Publish to agent's event channel."""
        channel = self.CHANNELS["events"].format(id=agent_id)
        return await self.publish(channel, message)

    async def publish_mission_update(
        self,
        mission_id: str,
        message: AgentMessage,
    ) -> int:
        """Publish mission update."""
        channel = self.CHANNELS["mission_updates"].format(id=mission_id)
        return await self.publish(channel, message)

    async def publish_skill_share(
        self,
        message: AgentMessage,
    ) -> int:
        """Publish skill share event."""
        return await self.publish(self.CHANNELS["skill_share"], message)

    async def subscribe(self, channel: str):
        """Subscribe to a channel."""
        if not self._client:
            return
        if not self._pubsub:
            self._pubsub = self._client.pubsub()
        await self._pubsub.subscribe(channel)
        return self._pubsub

    async def get_queue_depth(self, channel: str) -> int:
        """Get the depth of a channel's message queue."""
        if not self._client:
            return 0
        try:
            return await self._client.llen(channel)
        except Exception:
            return 0

    async def get_agent_queue_depth(self, agent_id: str) -> int:
        """Get agent task queue depth."""
        channel = self.CHANNELS["tasks"].format(id=agent_id)
        return await self.get_queue_depth(channel)

    async def push_task(
        self,
        agent_id: str,
        task: dict,
    ) -> bool:
        """Push task to agent's queue."""
        if not self._client:
            return False
        channel = self.CHANNELS["tasks"].format(id=agent_id)
        try:
            await self._client.rpush(channel, json.dumps(task))
            return True
        except Exception as e:
            logger.error(f"Failed to push task: {e}")
            return False

    async def pop_task(self, agent_id: str, timeout: int = 0) -> dict | None:
        """Pop task from agent's queue."""
        if not self._client:
            return None
        channel = self.CHANNELS["tasks"].format(id=agent_id)
        try:
            if timeout > 0:
                result = await self._client.blpop(channel, timeout=timeout)
                if result:
                    return json.loads(result[1])
            else:
                result = await self._client.lpop(channel)
                if result:
                    return json.loads(result)
        except Exception as e:
            logger.error(f"Failed to pop task: {e}")
        return None


# Global instance
_message_bus: SwarmMessageBus | None = None


async def get_message_bus() -> SwarmMessageBus:
    """Get or create global message bus instance."""
    global _message_bus
    if _message_bus is None:
        _message_bus = SwarmMessageBus()
        await _message_bus.connect()
    return _message_bus


async def close_message_bus() -> None:
    """Close global message bus."""
    global _message_bus
    if _message_bus:
        await _message_bus.disconnect()
        _message_bus = None
