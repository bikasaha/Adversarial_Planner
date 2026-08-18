import argparse
import csv
import json
from pathlib import Path

from adversarial_planner.agents import RuleBasedAgent, OpenAIAgent
from adversarial_planner.runner import AdversarialPlannerRunner


def load_dataset(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_outputs(results, output_dir: Path, run_id: str):
    output_dir.mkdir(parents=True, exist_ok=True)

    trajectories_path = output_dir / f"trajectories_{run_id}.json"
    metrics_path = output_dir / f"metrics_{run_id}.json"
    summary_path = output_dir / f"summary_{run_id}.csv"

    with open(trajectories_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    metrics = [
        {"scenario_id": r["scenario_id"], **r["metrics"]}
        for r in results
    ]

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    if metrics:
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(metrics[0].keys()))
            writer.writeheader()
            writer.writerows(metrics)

    return trajectories_path, metrics_path, summary_path


def main():
    parser = argparse.ArgumentParser(description="Run Adversarial_Planner framework experiments.")
    parser.add_argument("--dataset", default="data/adversarial_planner_dataset_50_scenarios.json")
    parser.add_argument("--agent", choices=["rule", "openai"], default="rule")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--run-id", default="default")

    args = parser.parse_args()

    dataset = load_dataset(args.dataset)[: args.limit]

    if args.agent == "rule":
        agent = RuleBasedAgent()
    else:
        agent = OpenAIAgent()

    runner = AdversarialPlannerRunner(agent=agent, max_rounds=args.max_rounds)
    results = []

    for scenario in dataset:
        print(f"Running scenario: {scenario.get('scenario_id')}")
        result = runner.run_scenario(scenario)
        results.append(result)
        print(f"  Metrics: {result['metrics']}")

    paths = write_outputs(results, Path(args.output_dir), args.run_id)

    print("\nFinished.")
    print(f"Trajectories: {paths[0]}")
    print(f"Metrics:      {paths[1]}")
    print(f"Summary CSV:  {paths[2]}")


if __name__ == "__main__":
    main()
