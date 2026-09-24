#! /usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_bpp
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


def generate_problem(n, c, weights, blind=False):
    lines = [
        "object_numbers:",
        f"      item: {n}",
        "target:",
        "      unpacked: [ " + ", ".join([str(j) for j in range(n)]) + " ]",
        "      residual: 0",
        "      bin-number: 0",
        "table_values:",
        f"      capacity: {c}",
        "      weight: { " + ", ".join([f"{j}: {weights[j]}" for j in range(n)]) + " }",
    ]

    if not blind:
        lines += [
            "      lb2-weight1: { "
            + ", ".join([f"{j}: {1}" for j in range(n) if weights[j] > c / 2])
            + " }",
            "      lb2-weight2: { "
            + ", ".join([f"{j}: {0.5}" for j in range(n) if weights[j] == c / 2])
            + " }",
            "      lb3-weight: { "
            + ", ".join(
                [
                    f"{j}: {1.0}"
                    if weights[j] > c * 2 / 3
                    else f"{j}: {2 / 3 // 0.001 / 1000}"
                    if weights[j] == c * 2 / 3
                    else f"{j}: {0.5}"
                    if weights[j] > c / 3
                    else f"{j}: {1 / 3 // 0.001 / 1000}"
                    for j in range(n)
                    if weights[j] >= c / 3
                ]
            )
            + " }",
        ]

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()

    n, c, weights = read_bpp.read(args.input)
    problem = generate_problem(n, c, weights)

    with open("problem.yaml", "w") as f:
        f.write(problem)

    if args.blind:
        domain_path = os.path.join(os.path.dirname(__file__), "domain_blind.yaml")
    else:
        domain_path = os.path.join(os.path.dirname(__file__), "domain.yaml")

    if args.didp_path is not None:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        print(f"Preprocessing time: {time.perf_counter() - start}s")
        subprocess.run(
            [args.didp_path, domain_path, "problem.yaml", args.config_path],
            preexec_fn=fn,
        )

    if os.path.exists("solution.yaml"):
        with open("solution.yaml") as f:
            result = yaml.safe_load(f)
        cost = round(result["cost"])
        solution = []
        for transition in result["transitions"]:
            if transition["name"] == "open-and-pack":
                solution.append([])
            solution[-1].append(transition["parameters"]["i"])

        print(solution)
        print(f"cost: {cost}")

        validation_result = read_bpp.validate(n, c, weights, solution, cost)
        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print(f"Execution time: {end - start}s")
