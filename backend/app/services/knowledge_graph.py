"""
Knowledge Graph Service - Neo4j for skill mapping and collaboration discovery.

Manages agent relationships, skill taxonomy, expertise mapping,
and discovers collaboration opportunities between agents.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class NodeType(str, Enum):
    """Knowledge graph node types."""
    AGENT = "agent"
    SKILL = "skill"
    TASK = "task"
    DOMAIN = "domain"
    CONCEPT = "concept"


class RelationshipType(str, Enum):
    """Knowledge graph relationship types."""
    HAS_SKILL = "has_skill"
    EXPERT_IN = "expert_in"
    CAN_COLLABORATE = "can_collaborate"
    COMPLEMENTS = "complements"
    SIMILAR_TO = "similar_to"
    WORKED_ON = "worked_on"
    LEARNED_FROM = "learned_from"
    TAUGHT = "taught"


class SkillLevel(str, Enum):
    """Agent skill proficiency levels."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


@dataclass
class AgentNode:
    """Agent node in knowledge graph."""
    agent_id: str
    name: str
    role: str
    expertise: list[str] = field(default_factory=list)
    skills: dict[str, SkillLevel] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    collaboration_preferences: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SkillNode:
    """Skill node in knowledge graph."""
    skill_id: str
    name: str
    category: str
    description: str
    related_skills: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class CollaborationOpportunity:
    """Collaboration opportunity between agents."""
    id: str
    agent_a_id: str
    agent_b_id: str
    collaboration_type: str
    match_score: float
    shared_skills: list[str] = field(default_factory=list)
    complementary_skills: list[str] = field(default_factory=list)
    recommended_approach: str = ""


class KnowledgeGraph:
    """Manages knowledge graph for agent network."""

    def __init__(self):
        self._agents: dict[str, AgentNode] = {}
        self._skills: dict[str, SkillNode] = {}
        self._relationships: list[tuple[str, RelationshipType, str]] = []
        self._collaboration_history: dict[str, list] = {}

    def register_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        expertise: list[str],
        capabilities: list[str],
        collaboration_preferences: list[str] = None,
    ) -> AgentNode:
        """Register agent in knowledge graph."""
        agent = AgentNode(
            agent_id=agent_id,
            name=name,
            role=role,
            expertise=expertise,
            capabilities=capabilities,
            collaboration_preferences=collaboration_preferences or [],
        )
        self._agents[agent_id] = agent

        for skill in expertise:
            self._relationships.append((agent_id, RelationshipType.HAS_SKILL, skill))

        return agent

    def update_agent_skills(
        self,
        agent_id: str,
        skills: dict[str, SkillLevel],
    ) -> bool:
        """Update agent's skill levels."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        agent.skills = skills
        for skill, level in skills.items():
            if level in (SkillLevel.EXPERT, SkillLevel.MASTER):
                self._relationships.append(
                    (agent_id, RelationshipType.EXPERT_IN, skill)
                )

        return True

    def add_skill(
        self,
        name: str,
        category: str,
        description: str,
        related_skills: list[str] = None,
        prerequisites: list[str] = None,
    ) -> SkillNode:
        """Add skill to knowledge graph."""
        skill = SkillNode(
            skill_id=str(uuid.uuid4()),
            name=name,
            category=category,
            description=description,
            related_skills=related_skills or [],
            prerequisites=prerequisites or [],
        )
        self._skills[skill.skill_id] = skill
        self._skills[name] = skill

        for related in (related_skills or []):
            self._relationships.append(
                (name, RelationshipType.SIMILAR_TO, related)
            )

        return skill

    def get_agent(self, agent_id: str) -> Optional[AgentNode]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def find_skill_experts(
        self,
        skill: str,
        min_level: SkillLevel = SkillLevel.ADVANCED,
    ) -> list[AgentNode]:
        """Find agents with expertise in a skill."""
        level_order = [
            SkillLevel.NOVICE,
            SkillLevel.BEGINNER,
            SkillLevel.INTERMEDIATE,
            SkillLevel.ADVANCED,
            SkillLevel.EXPERT,
            SkillLevel.MASTER,
        ]
        min_index = level_order.index(min_level)

        experts = []
        for agent in self._agents.values():
            skill_level = agent.skills.get(skill)
            if skill_level and level_order.index(skill_level) >= min_index:
                experts.append(agent)

        return sorted(
            experts,
            key=lambda a: level_order.index(a.skills[skill]),
            reverse=True,
        )

    def discover_collaboration(
        self,
        agent_id: str,
        max_results: int = 10,
    ) -> list[CollaborationOpportunity]:
        """Discover collaboration opportunities for an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return []

        opportunities = []

        for other_id, other in self._agents.items():
            if other_id == agent_id:
                continue

            match_score = self._calculate_match_score(agent, other)

            if match_score < 0.3:
                continue

            shared = set(agent.expertise) & set(other.expertise)
            complementary = self._find_complementary_skills(agent, other)

            opportunity = CollaborationOpportunity(
                id=str(uuid.uuid4()),
                agent_a_id=agent_id,
                agent_b_id=other_id,
                collaboration_type=self._determine_collaboration_type(shared, complementary),
                match_score=match_score,
                shared_skills=list(shared),
                complementary_skills=complementary,
                recommended_approach=self._recommend_approach(shared, complementary),
            )
            opportunities.append(opportunity)

        return sorted(opportunities, key=lambda o: o.match_score, reverse=True)[:max_results]

    def _calculate_match_score(self, agent_a: AgentNode, agent_b: AgentNode) -> float:
        """Calculate collaboration match score."""
        shared_expertise = len(set(agent_a.expertise) & set(agent_b.expertise))
        total_expertise = len(set(agent_a.expertise) | set(agent_b.expertise))

        expertise_score = shared_expertise / total_expertise if total_expertise > 0 else 0

        skill_overlap = sum(
            1 for skill in agent_a.skills
            if skill in agent_b.skills
        )
        skill_compatibility = skill_overlap / max(len(agent_a.skills), 1)

        pref_match = len(
            set(agent_a.collaboration_preferences) & set(agent_b.collaboration_preferences)
        )
        preference_score = pref_match / max(
            len(agent_a.collaboration_preferences), len(agent_b.collaboration_preferences), 1
        )

        return (expertise_score * 0.5) + (skill_compatibility * 0.3) + (preference_score * 0.2)

    def _find_complementary_skills(self, agent_a: AgentNode, agent_b: AgentNode) -> list[str]:
        """Find complementary skills between agents."""
        a_skills = set(agent_a.skills.keys())
        b_skills = set(agent_b.skills.keys())

        a_weak = {s for s, l in agent_a.skills.items() if l in (SkillLevel.NOVICE, SkillLevel.BEGINNER)}
        b_weak = {s for s, l in agent_b.skills.items() if l in (SkillLevel.NOVICE, SkillLevel.BEGINNER)}

        b_strong = b_skills - a_skills
        a_strong = a_skills - b_skills

        return list((a_weak & b_strong) | (b_weak & a_strong))

    def _determine_collaboration_type(
        self,
        shared_skills: set,
        complementary_skills: list[str],
    ) -> str:
        """Determine best collaboration type."""
        if len(shared_skills) > 3:
            return "peer_review"
        elif complementary_skills:
            return "skill_mentorship"
        else:
            return "knowledge_sharing"

    def _recommend_approach(
        self,
        shared_skills: set,
        complementary_skills: list[str],
    ) -> str:
        """Recommend collaboration approach."""
        if len(shared_skills) > 3:
            return "Joint project with peer review at each milestone"
        elif complementary_skills:
            return f"Pair programming: mentor in {complementary_skills[0]}, mentee learns"
        else:
            return "Weekly knowledge sharing sessions"

    def record_collaboration(
        self,
        agent_a_id: str,
        agent_b_id: str,
        outcome: str,
        shared_skills: list[str],
    ) -> bool:
        """Record successful collaboration."""
        key = f"{min(agent_a_id, agent_b_id)}:{max(agent_a_id, agent_b_id)}"

        if key not in self._collaboration_history:
            self._collaboration_history[key] = []

        self._collaboration_history[key].append({
            "timestamp": datetime.utcnow(),
            "outcome": outcome,
            "shared_skills": shared_skills,
        })

        self._relationships.append(
            (agent_a_id, RelationshipType.WORKED_ON, agent_b_id)
        )
        self._relationships.append(
            (agent_b_id, RelationshipType.WORKED_ON, agent_a_id)
        )

        return True

    def get_skill_taxonomy(self, category: Optional[str] = None) -> list[SkillNode]:
        """Get skill taxonomy."""
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    def find_related_skills(self, skill: str) -> list[str]:
        """Find skills related to given skill."""
        skill_node = self._skills.get(skill)
        if not skill_node:
            return []
        return skill_node.related_skills

    def get_agent_network(
        self,
        agent_id: str,
        depth: int = 2,
    ) -> dict:
        """Get agent's network connections."""
        agent = self._agents.get(agent_id)
        if not agent:
            return {}

        network = {"direct": [], "indirect": []}

        for src, rel, tgt in self._relationships:
            if src == agent_id and tgt in self._agents:
                network["direct"].append({
                    "relationship": rel.value,
                    "target": tgt,
                })

        if depth >= 2:
            for direct in network["direct"]:
                for src, rel, tgt in self._relationships:
                    if src == direct["target"] and tgt in self._agents and tgt != agent_id:
                        network["indirect"].append({
                            "relationship": rel.value,
                            "target": tgt,
                            "via": direct["target"],
                        })

        return network

    def get_knowledge_stats(self) -> dict:
        """Get knowledge graph statistics."""
        return {
            "total_agents": len(self._agents),
            "total_skills": len(self._skills),
            "total_relationships": len(self._relationships),
            "collaboration_pairs": len(self._collaboration_history),
            "skill_categories": len(set(s.category for s in self._skills.values())),
        }


_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Get global knowledge graph service."""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph
