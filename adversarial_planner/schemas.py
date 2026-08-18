from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class BeliefState:
    confirmed_facts: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    potential_attack_paths: List[str] = field(default_factory=list)
    ruled_out_paths: List[str] = field(default_factory=list)
    detection_considerations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def add_unique(self, field_name: str, items: List[str]) -> None:
        target = getattr(self, field_name)
        for item in items:
            if item and item not in target:
                target.append(item)


@dataclass
class AgentAction:
    action: str
    action_justification: str = ""
    expected_outcome: str = ""
    fallback_plan: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnvironmentFeedback:
    status: str
    evidence: List[str] = field(default_factory=list)
    new_observation: List[str] = field(default_factory=list)
    detection_risk: str = "low"
    objective_achieved: bool = False
    dependency_valid: bool = True
    invalid_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrajectoryStep:
    round_id: int
    belief_before: Dict[str, Any]
    action: Dict[str, Any]
    feedback: Dict[str, Any]
    belief_after: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
