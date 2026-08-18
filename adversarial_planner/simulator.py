from typing import Any, Dict, List, Set
from .schemas import EnvironmentFeedback


class EnvironmentSimulator:
    """
    Lightweight semantic simulator.

    It does not execute real cyber operations. It maps high-level abstract actions
    to simulator feedback using hidden scenario truth and internal progress state.
    """

    def __init__(self, scenario: Dict[str, Any]):
        self.scenario = scenario
        self.hidden = scenario.get("hidden_environment_truth", {})
        self.rules = scenario.get("environment_rules", {})
        self.progress: Set[str] = set()
        self.failed_actions: Set[str] = set()
        self.risk_history: List[str] = []

    def evaluate(self, action: str) -> EnvironmentFeedback:
        action = action.strip().lower()

        # Dependency validation first
        dep_valid, dep_reason = self._check_dependencies(action)
        if not dep_valid:
            self.failed_actions.add(action)
            return EnvironmentFeedback(
                status="failure",
                evidence=[f"Action dependency invalid: {dep_reason}"],
                detection_risk="medium",
                dependency_valid=False,
                invalid_reason=dep_reason
            )

        # Use explicit dataset rules when action is provided
        explicit = self._lookup_explicit_rule(action)
        if explicit is not None:
            return self._feedback_from_rule(action, explicit)

        # Otherwise use semantic fallback logic
        return self._semantic_feedback(action)

    def _lookup_explicit_rule(self, action: str):
        for rule in self.rules.get("example_actions", []):
            if rule.get("action", "").lower() == action:
                return rule
        return None

    def _feedback_from_rule(self, action: str, rule: Dict[str, Any]) -> EnvironmentFeedback:
        result = rule.get("possible_result", rule.get("status", "failure"))
        risk = rule.get("detection_risk", "low")
        self.risk_history.append(risk)

        if result == "success":
            self.progress.add(action)

        evidence = []
        new_obs = []

        if action == "vpn_exploit":
            if result == "success":
                new_obs.append("VPN access established")
                self.progress.add("initial_access")
            else:
                evidence.append("VPN exploitation failed or target appears patched")
        elif action == "gitlab_recon":
            if result == "success":
                new_obs.append("Repository exposure investigated")
                if self._developer_token_exists():
                    new_obs.append("Developer token exposed in repository or CI/CD configuration")
                    self.progress.add("developer_token_found")
            else:
                evidence.append("No useful GitLab exposure found")

        return EnvironmentFeedback(
            status=result,
            evidence=evidence,
            new_observation=new_obs,
            detection_risk=risk,
            objective_achieved=False
        )

    def _semantic_feedback(self, action: str) -> EnvironmentFeedback:
        risk = "low"

        if action == "service_enum":
            self.progress.add("service_enum")
            return EnvironmentFeedback(
                status="success",
                new_observation=["Visible services enumerated and prioritized"],
                detection_risk="low"
            )

        if action == "vpn_exploit":
            patched = self.hidden.get("credential_constraints", {}).get("service_actually_patched", False)
            if patched or "patched_service" in self.hidden.get("twists", []):
                self.failed_actions.add(action)
                return EnvironmentFeedback(
                    status="failure",
                    evidence=["VPN exploit attempt unsuccessful", "Target likely patched"],
                    detection_risk="medium"
                )
            self.progress.add("initial_access")
            return EnvironmentFeedback(
                status="success",
                new_observation=["VPN access established"],
                detection_risk="medium"
            )

        if action == "gitlab_recon":
            self.progress.add("gitlab_recon")
            if self._developer_token_exists() or "hidden_token" in self.hidden.get("twists", []):
                self.progress.add("developer_token_found")
                return EnvironmentFeedback(
                    status="success",
                    new_observation=["Developer token exposed in repository or CI/CD configuration"],
                    detection_risk="low"
                )
            return EnvironmentFeedback(
                status="partial_success",
                new_observation=["Public repositories discovered but no direct secret found"],
                detection_risk="low"
            )

        if action == "jenkins_recon":
            self.progress.add("jenkins_recon")
            if "internal_secret_exposure" in self.hidden.get("twists", []):
                self.progress.add("developer_token_found")
                return EnvironmentFeedback(
                    status="success",
                    new_observation=["CI job logs reveal service token"],
                    detection_risk="low"
                )
            return EnvironmentFeedback(
                status="partial_success",
                new_observation=["CI/CD system identified but access is limited"],
                detection_risk="medium"
            )

        if action == "credential_attack":
            if self.hidden.get("credential_constraints", {}).get("mfa_blocks_admin_login", False):
                self.failed_actions.add(action)
                return EnvironmentFeedback(
                    status="failure",
                    evidence=["Credential attempt blocked by MFA or conditional access"],
                    detection_risk="high"
                )
            self.progress.add("initial_access")
            return EnvironmentFeedback(
                status="success",
                new_observation=["Credential-based access established"],
                detection_risk="high"
            )

        if action == "developer_token_use":
            if "developer_token_found" not in self.progress:
                self.failed_actions.add(action)
                return EnvironmentFeedback(
                    status="failure",
                    evidence=["No valid developer token has been confirmed"],
                    detection_risk="medium",
                    dependency_valid=False,
                    invalid_reason="developer_token_use requires confirmed token discovery"
                )
            self.progress.add("developer_access")
            return EnvironmentFeedback(
                status="success",
                new_observation=["Developer access established", "Internal Docker registry discovered"],
                detection_risk="low"
            )

        if action == "registry_secret_search":
            if "developer_access" not in self.progress:
                self.failed_actions.add(action)
                return EnvironmentFeedback(
                    status="failure",
                    evidence=["Internal registry is not reachable without developer access"],
                    detection_risk="medium",
                    dependency_valid=False,
                    invalid_reason="registry_secret_search requires developer access"
                )
            self.progress.add("db_credential")
            return EnvironmentFeedback(
                status="success",
                new_observation=["Database credential discovered in registry configuration"],
                detection_risk="medium"
            )

        if action == "lateral_movement":
            if "initial_access" not in self.progress and "developer_access" not in self.progress:
                self.failed_actions.add(action)
                return EnvironmentFeedback(
                    status="failure",
                    evidence=["Lateral movement requires an established foothold"],
                    detection_risk="high",
                    dependency_valid=False,
                    invalid_reason="lateral_movement requires initial access or developer access"
                )
            self.progress.add("internal_access")
            return EnvironmentFeedback(
                status="success",
                new_observation=["Internal host reachable"],
                detection_risk="high"
            )

        if action == "database_access":
            if "db_credential" not in self.progress and "internal_access" not in self.progress:
                self.failed_actions.add(action)
                return EnvironmentFeedback(
                    status="failure",
                    evidence=["Database access requires confirmed credential or internal access"],
                    detection_risk="medium",
                    dependency_valid=False,
                    invalid_reason="database_access requires db credential or internal access"
                )
            self.progress.add("objective_achieved")
            return EnvironmentFeedback(
                status="success",
                new_observation=["Objective achieved: target data store accessed in simulation"],
                detection_risk="low",
                objective_achieved=True
            )

        if action == "stealth_pause":
            return EnvironmentFeedback(
                status="success",
                new_observation=["Agent pauses high-risk activity and reassesses lower-noise options"],
                detection_risk="low"
            )

        self.failed_actions.add(action)
        return EnvironmentFeedback(
            status="failure",
            evidence=[f"Unknown or unsupported action: {action}"],
            detection_risk="medium"
        )

    def _developer_token_exists(self) -> bool:
        return self.hidden.get("credential_constraints", {}).get("developer_token_exists", False)

    def _check_dependencies(self, action: str):
        if action == "developer_token_use" and "developer_token_found" not in self.progress:
            return False, "developer token not confirmed"
        if action == "registry_secret_search" and "developer_access" not in self.progress:
            return False, "developer access not established"
        if action == "database_access" and "db_credential" not in self.progress and "internal_access" not in self.progress:
            return False, "database credential/internal access not established"
        if action == "lateral_movement" and "initial_access" not in self.progress and "developer_access" not in self.progress:
            return False, "no foothold available"
        return True, ""
