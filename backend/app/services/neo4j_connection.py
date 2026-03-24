"""
Neo4j Connection Manager for Knowledge Graph.

Provides connection pooling and query execution for Neo4j database.
"""
import os

from pydantic import BaseModel


class Neo4jConfig(BaseModel):
    """Neo4j connection configuration."""
    uri: str = "bolt://neo4j:7687"
    user: str = "neo4j"
    password: str = ""
    database: str = "neo4j"


class Neo4jConnection:
    """Neo4j connection manager."""

    def __init__(self, config: Neo4jConfig | None = None):
        self.config = config or Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", ""),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
        )
        self._driver = None

    def connect(self) -> bool:
        """Connect to Neo4j."""
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password)
            )
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def execute_query(
        self,
        query: str,
        parameters: dict | None = None,
    ) -> list[dict]:
        """Execute Cypher query."""
        if not self._driver:
            return []

        try:
            with self._driver.session(database=self.config.database) as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception:
            return []

    def execute_write(
        self,
        query: str,
        parameters: dict | None = None,
    ) -> bool:
        """Execute write query."""
        if not self._driver:
            return False

        try:
            with self._driver.session(database=self.config.database) as session:
                session.run(query, parameters or {})
                return True
        except Exception:
            return False

    def is_connected(self) -> bool:
        """Check if connected to Neo4j."""
        if not self._driver:
            return False

        try:
            with self._driver.session() as session:
                session.run("RETURN 1")
                return True
        except Exception:
            return False

    def create_agent_node(
        self,
        agent_id: str,
        name: str,
        role: str,
    ) -> bool:
        """Create agent node in Neo4j."""
        query = """
        CREATE (a:Agent {
            agent_id: $agent_id,
            name: $name,
            role: $role,
            created_at: datetime()
        })
        RETURN a
        """
        return self.execute_write(query, {"agent_id": agent_id, "name": name, "role": role})

    def create_skill_relationship(
        self,
        agent_id: str,
        skill: str,
        level: str,
    ) -> bool:
        """Create KNOWS relationship between agent and skill."""
        query = """
        MERGE (s:Skill {name: $skill})
        WITH s
        MATCH (a:Agent {agent_id: $agent_id})
        MERGE (a)-[r:KNOWS {level: $level}]->(s)
        RETURN r
        """
        return self.execute_write(query, {"agent_id": agent_id, "skill": skill, "level": level})

    def create_collaboration_relationship(
        self,
        agent_a_id: str,
        agent_b_id: str,
        outcome: str,
    ) -> bool:
        """Create COLLABORATED_WITH relationship."""
        query = """
        MATCH (a:Agent {agent_id: $agent_a_id})
        MATCH (b:Agent {agent_id: $agent_b_id})
        MERGE (a)-[r:COLLABORATED_WITH {outcome: $outcome, timestamp: datetime()}]->(b)
        RETURN r
        """
        return self.execute_write(query, {"agent_a_id": agent_a_id, "agent_b_id": agent_b_id, "outcome": outcome})

    def find_skill_experts(self, skill: str, min_level: str = "expert") -> list[dict]:
        """Find agents expert in a skill."""
        query = """
        MATCH (a:Agent)-[r:KNOWS]->(s:Skill {name: $skill})
        WHERE r.level IN $levels
        RETURN a.agent_id as agent_id, a.name as name, r.level as level
        ORDER BY r.level DESC
        LIMIT 10
        """
        levels = {"expert": ["expert", "master"], "advanced": ["advanced", "expert", "master"]}
        return self.execute_query(query, {"skill": skill, "levels": levels.get(min_level, ["expert", "master"])})

    def get_agent_network(self, agent_id: str) -> list[dict]:
        """Get agent's collaboration network."""
        query = """
        MATCH (a:Agent {agent_id: $agent_id})-[r:COLLABORATED_WITH]->(b:Agent)
        RETURN b.agent_id as agent_id, b.name as name, r.outcome as outcome, r.timestamp as timestamp
        """
        return self.execute_query(query, {"agent_id": agent_id})

    def get_knowledge_stats(self) -> dict:
        """Get knowledge graph statistics."""
        agents = self.execute_query("MATCH (a:Agent) RETURN count(a) as count")
        skills = self.execute_query("MATCH (s:Skill) RETURN count(s) as count")
        collabs = self.execute_query("MATCH ()-[r:COLLABORATED_WITH]->() RETURN count(r) as count")

        return {
            "total_agents": agents[0].get("count", 0) if agents else 0,
            "total_skills": skills[0].get("count", 0) if skills else 0,
            "total_collaborations": collabs[0].get("count", 0) if collabs else 0,
        }


_neo4j_connection: Neo4jConnection | None = None


def get_neo4j_connection() -> Neo4jConnection:
    """Get global Neo4j connection."""
    global _neo4j_connection
    if _neo4j_connection is None:
        _neo4j_connection = Neo4jConnection()
    return _neo4j_connection
