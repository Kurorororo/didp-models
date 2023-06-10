#! /usr/bin/env python3

import argparse
import os
import time
import subprocess
import resource

import yaml

import read_bpp


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


def generate_problem(name, n, c, weights):
    lines = [
        "domain: BPP",
        "problem: {}".format(name),
        "object_numbers:",
        "      item: {}".format(n),
        "target:",
        "      unpacked: [ " + ", ".join([str(j) for j in range(n)]) + " ]",
        "      residual: 0",
        "      bin-number: 0",
        "table_values:",
        "      capacity: {}".format(c),
        "      weight: { "
        + ", ".join(["{}: {}".format(j, weights[j]) for j in range(n)])
        + " }",
    ]
    lines += [
        "      lb2-weight1: { "
        + ", ".join(["{}: {}".format(j, 1) for j in range(n) if weights[j] > c / 2])
        + " }",
        "      lb2-weight2: { "
        + ", ".join(["{}: {}".format(j, 0.5) for j in range(n) if weights[j] == c / 2])
        + " }",
        "      lb3-weight: { "
        + ", ".join(
            [
                "{}: {}".format(j, 1.0)
                if weights[j] > c * 2 / 3
                else "{}: {}".format(j, 2 / 3 // 0.001 / 1000)
                if weights[j] == c * 2 / 3
                else "{}: {}".format(j, 0.5)
                if weights[j] > c / 3
                else "{}: {}".format(j, 1 / 3 // 0.001 / 1000)
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
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    args = parser.parse_args()

    n, c, weights = read_bpp.read(args.input)
    name = os.path.basename(args.input)
    problem = generate_problem(name, n, c, weights)

    with open("problem.yaml", "w") as f:
        f.write(problem)

    if args.continuous:
        domain_path = os.path.join(os.path.dirname(__file__), "domain-continuous.yaml")
    else:
        domain_path = os.path.join(os.path.dirname(__file__), "domain.yaml")

    if args.didp_path is not None:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        print("Preprocessing time: {}s".format(time.perf_counter() - start))
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
        print("cost: {}".format(cost))

        validation_result = read_bpp.validate(n, c, weights, solution, cost)
        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
