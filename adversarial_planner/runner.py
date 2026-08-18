from typing import Any, Dict, List
from .agents import BaseAgent
from .evaluator import Evaluator
from .simulator import EnvironmentSimulator


class AdversarialPlannerRunner:
    def __init__(self, agent: BaseAgent, max_rounds: int = 6):
        self.agent = agent
        self.max_rounds = max_rounds
        self.evaluator = Evaluator()

    def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        simulator = EnvironmentSimulator(scenario)
        belief = self.agent.initialize_belief(scenario)
        trajectory: List[Dict[str, Any]] = []

        for round_id in range(1, self.max_rounds + 1):
            belief_before = belief.to_dict()
            action = self.agent.choose_action(scenario, belief, trajectory)
            feedback = simulator.evaluate(action.action)
            belief = self.agent.update_belief(belief, action, feedback)

            step = {
                "round_id": round_id,
                "belief_before": belief_before,
                "action": action.to_dict(),
                "feedback": feedback.to_dict(),
                "belief_after": belief.to_dict(),
            }
            trajectory.append(step)

            if feedback.objective_achieved:
                break

        metrics = self.evaluator.evaluate(trajectory)

        return {
            "scenario_id": scenario.get("scenario_id", "unknown"),
            "trajectory": trajectory,
            "metrics": metrics
        }
