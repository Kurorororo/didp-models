#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_graph_clear
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


def generate_problem(n, node_weights, edge_weiths):
    lines = [
        "object_numbers:",
        "   node: {}".format(n),
        "target:",
        "   clean: []",
        "table_values:",
        "   all-nodes: [ " + ", ".join(str(i) for i in range(n)) + " ]",
        "   a: { "
        + ", ".join("{}: {}".format(i, node_weights[i]) for i in range(n))
        + " }",
        "   b: {",
    ]

    for i in range(n):
        line = "        "
        for j in range(n):
            if (i, j) in edge_weiths:
                line += "[{}, {}]: {}, ".format(i, j, edge_weiths[i, j])
            elif (j, i) in edge_weiths:
                line += "[{}, {}]: {}, ".format(i, j, edge_weiths[j, i])
        lines.append(line)
    lines.append("     }")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    args = parser.parse_args()

    n, a, b = read_graph_clear.read(args.input)
    name = os.path.basename(args.input)
    problem = generate_problem(n, a, b)

    with open("problem.yaml", "w") as f:
        f.write(problem)

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
            solution.append(transition["parameters"]["c"])

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_graph_clear.validate(n, a, b, solution, cost)

        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
