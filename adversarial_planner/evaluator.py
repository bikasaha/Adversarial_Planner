from typing import Any, Dict, List


class Evaluator:
    def evaluate(self, trajectory: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not trajectory:
            return {}

        actions = [s["action"]["action"] for s in trajectory]
        feedbacks = [s["feedback"] for s in trajectory]
        failures = [i for i, f in enumerate(feedbacks) if f.get("status") == "failure"]
        objective = any(f.get("objective_achieved", False) for f in feedbacks)

        repeated_failed = 0
        failed_actions = set()
        for s in trajectory:
            action = s["action"]["action"]
            status = s["feedback"].get("status")
            if status == "failure":
                if action in failed_actions:
                    repeated_failed += 1
                failed_actions.add(action)

        dependency_invalid = sum(1 for f in feedbacks if not f.get("dependency_valid", True))
        high_or_medium_risk = [i for i, f in enumerate(feedbacks) if f.get("detection_risk") in {"medium", "high"}]

        # Negative evidence utilization: after failed action, did the same action avoid repetition?
        neu_scores = []
        for idx in failures:
            failed_action = actions[idx]
            repeated_later = failed_action in actions[idx + 1:]
            neu_scores.append(0 if repeated_later else 1)
        negative_evidence_utilization = sum(neu_scores) / len(neu_scores) if neu_scores else 1.0

        # Replanning success: after a failure, was a later non-failed action found?
        replanning_scores = []
        for idx in failures:
            recovered = any(f.get("status") in {"success", "partial_success"} for f in feedbacks[idx + 1:])
            replanning_scores.append(1 if recovered else 0)
        replanning_success_rate = sum(replanning_scores) / len(replanning_scores) if replanning_scores else 1.0

        # Detection awareness: after medium/high risk, did agent avoid immediately repeating the same action?
        da_scores = []
        for idx in high_or_medium_risk:
            if idx + 1 < len(actions):
                da_scores.append(1 if actions[idx + 1] != actions[idx] else 0)
        detection_awareness = sum(da_scores) / len(da_scores) if da_scores else 1.0

        # State consistency: simple proxy, no repeated failed action and no dependency invalidity
        state_consistency = 1.0
        if repeated_failed > 0:
            state_consistency -= 0.4
        if dependency_invalid > 0:
            state_consistency -= 0.4
        state_consistency = max(0.0, state_consistency)

        return {
            "task_success": int(objective),
            "rounds_used": len(trajectory),
            "replanning_success_rate": round(replanning_success_rate, 3),
            "negative_evidence_utilization": round(negative_evidence_utilization, 3),
            "dependency_validity": round(1 - (dependency_invalid / len(trajectory)), 3),
            "looping_rate": round(repeated_failed / len(trajectory), 3),
            "detection_awareness": round(detection_awareness, 3),
            "state_consistency": round(state_consistency, 3),
        }
