#!/usr/bin/env python3
"""Export the original QTSP formulation to YAML-DyPDL."""

import argparse
import subprocess
from pathlib import Path

import qtsp_didp
import read_qtsp
import yaml


def create_didp(n, costs):
    cin, cmid, cout = qtsp_didp.cost_minima(costs)
    problem = dict(
        object_numbers=dict(node=n),
        target=dict(unvisited=list(range(1, n)), previous=0, current=0, first=0),
        table_values=dict(
            c={
                (i, j, k): costs[i][j][k]
                for i in range(n)
                for j in range(n)
                for k in range(n)
            },
            cin=dict(enumerate(cin)),
            cmid=dict(enumerate(cmid)),
            cout=dict(enumerate(cout)),
        ),
    )
    return yaml.safe_dump(problem, sort_keys=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--kind", choices=["angle", "angle-distance"], default="angle")
    parser.add_argument("--decimals", type=int, default=2)
    parser.add_argument("--didp-path", "-d")
    parser.add_argument(
        "--config-path",
        "-c",
        default=str(Path(__file__).resolve().parents[1] / "configs/cabs.yaml"),
    )
    parser.add_argument("--output", type=Path, default=Path("problem.yaml"))
    args = parser.parse_args()
    n, costs = read_qtsp.load_instance(args.input, args.kind, args.decimals)
    args.output.write_text(create_didp(n, costs))
    if args.didp_path:
        subprocess.run(
            [
                args.didp_path,
                str(Path(__file__).with_name("domain.yaml")),
                str(args.output),
                args.config_path,
            ],
            check=True,
        )
        solution_path = Path("solution.yaml")
        if solution_path.exists():
            result = yaml.safe_load(solution_path.read_text())
            tour = [0] + [t["parameters"]["to"] for t in result["transitions"]] + [0]
            if not read_qtsp.validate_tour(costs, tour, result["cost"]):
                raise RuntimeError("Invalid QTSP solution")
            print(tour)
            print(f"Cost: {result['cost'] / 10**args.decimals}")
            print("The solution is valid.")
