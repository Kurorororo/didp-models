#!/usr/bin/env python3

import argparse
import os
import time
import re
import resource
import subprocess

import yaml

import read_tsplib


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


def compute_min_distance_to(nodes, edges):
    result = {
        j: min([edges[i, j] for i in nodes if (i, j) in edges and i != j])
        for j in nodes
    }

    return result


def compute_min_distance_from(nodes, edges):
    result = {
        i: min([edges[i, j] for j in nodes if (i, j) in edges and i != j])
        for i in nodes
    }

    return result


def create_didp(problem_name, n, nodes, edges, capacity, demand, k, use_bound=False):
    output_lines = [
        "domain: CVRP",
        "problem: {}".format(problem_name),
        "object_numbers:",
        "      customer: {}".format(n),
        "target:",
        "      unvisited: [ " + ", ".join([str(i) for i in range(1, n)]) + " ]",
        "      location: 0",
        "      load: 0",
        "      vehicles: 1",
        "table_values:",
        "      max_vehicles: {}".format(k),
        "      capacity: {}".format(capacity),
        "      demand : { "
        + ", ".join(["{}: {}".format(i - 1, demand[i]) for i in nodes])
        + " }",
        "      distance:",
        "            {",
    ]
    for (i, j) in edges:
        output_lines.append(
            "                  [{}, {}]: {},".format(i - 1, j - 1, edges[i, j])
        )
    output_lines.append("      }")

    if use_bound:
        min_distance_to = compute_min_distance_to(nodes, edges)
        min_distance_from = compute_min_distance_from(nodes, edges)
        output_lines += [
            "      min_distance_to: { "
            + ", ".join("{}: {}".format(i - 1, min_distance_to[i]) for i in nodes)
            + " }",
            "      min_distance_from: { "
            + ", ".join("{}: {}".format(i - 1, min_distance_from[i]) for i in nodes)
            + " }",
        ]

    return "\n".join(output_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--use-bound", action="store_true")
    args = parser.parse_args()

    name = os.path.basename(args.input)
    m = re.match(r".+k(\d+).+", name)
    k = int(m.group(1))

    (
        n,
        nodes,
        edges,
        capacity,
        demand,
        depot,
        _,
    ) = read_tsplib.read_cvrp(args.input)
    problem = create_didp(
        name, n, nodes, edges, capacity, demand, k, use_bound=args.use_bound
    )

    with open("problem.yaml", "w") as f:
        f.write(problem)

    domain_file = "domain_bound.yaml" if args.use_bound else "domain.yaml"
    domain_path = os.path.join(os.path.dirname(__file__), domain_file)

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
        solution = [depot]
        for transition in result["transitions"]:
            if transition["name"] == "visit-via-depot":
                solution.append(depot)
                solution.append(transition["parameters"]["to"] + 1)
            if transition["name"] == "visit":
                solution.append(transition["parameters"]["to"] + 1)
            if transition["name"] == "return":
                solution.append(depot)

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_tsplib.validate_cvrp(
            n, nodes, edges, capacity, demand, depot, solution, cost, k=k
        )
        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
