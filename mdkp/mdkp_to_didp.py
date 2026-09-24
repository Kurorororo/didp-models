#!/usr/bin/env python3

import argparse
import math
import os
import resource
import subprocess
import time

import read_mdkp
import yaml

start = time.perf_counter()


def get_limit_resource(time_limit, memory_limit):
    def limit_resources():
        if time_limit is not None:
            resource.setrlimit(resource.RLIMIT_CPU, (time_limit, time_limit + 5))

        if memory_limit is not None:
            resource.setrlimit(
                resource.RLIMIT_AS,
                (memory_limit * 1024 * 1024, memory_limit * 1024 * 1024),
            )

    return limit_resources


def create_didp_domain(m, blind=False):
    domain = dict(
        domain="MDKP",
        reduce="max",
        cost_type="integer",
        objects=["item"],
        state_variables=[dict(name="j", type="element", object="item")]
        + [dict(name=f"r{i}", type="integer", preference="greater") for i in range(m)],
        tables=[
            dict(name="n_items", type="element"),
            dict(name="epsilon", type="continuous"),
            dict(name="profit", type="integer", args=["item"]),
            dict(name="reward", type="integer", args=["item"]),
            dict(name="remaining_items", type="set", object="item", args=["item"]),
        ]
        + [dict(name=f"w{i}", type="integer", args=["item"]) for i in range(m)],
        base_cases=[["(= j n_items)"]],
        transitions=[
            dict(
                name="pack",
                cost="(+ cost (profit j))",
                effect={
                    "j": "(+ j 1)",
                    **{f"r{i}": f"(- r{i} (w{i} j))" for i in range(m)},
                },
                preconditions=["(< j n_items)"]
                + [f"(>= r{i} (w{i} j))" for i in range(m)],
            ),
            dict(
                name="ignore",
                cost="cost",
                effect=dict(j="(+ j 1)"),
                preconditions=["(< j n_items)"],
            ),
        ],
    )
    if not blind:
        domain["dual_bounds"] = ["(sum reward (remaining_items j))"]
        for i in range(m):
            free = f"(filter x (remaining_items j) (= (w{i} x) 0))"
            positive = f"(filter x (remaining_items j) (> (w{i} x) 0))"
            domain["dual_bounds"].append(
                f"(floor (+ epsilon (+ (sum reward {free}) (fractional_knapsack {positive} r{i} reward w{i}))))"
            )
    return yaml.safe_dump(domain, sort_keys=False)


def create_didp_problem(n, m, profit, weight, capacity, epsilon=1e-6):
    if not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("epsilon must be finite and nonnegative")
    problem = dict(
        object_numbers=dict(item=n + 1),
        target={"j": 0, **{f"r{i}": capacity[i] for i in range(m)}},
        table_values=dict(
            n_items=n,
            epsilon=epsilon,
            profit=dict(enumerate(profit + [0])),
            reward=dict(enumerate([max(0, p) for p in profit] + [0])),
            remaining_items={j: list(range(j, n)) for j in range(n + 1)},
            **{f"w{i}": dict(enumerate(weight[i] + [0])) for i in range(m)},
        ),
    )
    return yaml.safe_dump(problem, sort_keys=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--epsilon", type=float, default=1e-6)
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()

    n, m, profit, weight, capacity = read_mdkp.read_mdkp(args.input)

    domain_file = create_didp_domain(m, blind=args.blind)

    with open("domain.yaml", "w") as f:
        f.write(domain_file)

    problem_file = create_didp_problem(
        n,
        m,
        profit,
        weight,
        capacity,
        epsilon=args.epsilon,
    )

    with open("problem.yaml", "w") as f:
        f.write(problem_file)

    if args.didp_path is not None:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        print(f"Preprocessing time: {time.perf_counter() - start}s")
        subprocess.run(
            [args.didp_path, "domain.yaml", "problem.yaml", args.config_path],
            preexec_fn=fn,
        )

    if os.path.exists("solution.yaml"):
        with open("solution.yaml") as f:
            result = yaml.safe_load(f)

        cost = result["cost"]
        solution = []

        for i, transition in enumerate(result["transitions"]):
            if transition["name"] == "pack":
                solution.append(i)

        print(solution)
        print(f"cost: {cost}")

        validation_result = read_mdkp.validate_mdkp(
            m, profit, weight, capacity, solution, cost
        )

        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print(f"Execution time: {end - start}s")
