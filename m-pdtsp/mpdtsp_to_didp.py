#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_tsplib
import yaml
from mpdtsp_util import (
    check_edge,
    compute_not_inferred_precedence,
    compute_precedence,
    compute_predecessors_and_successors,
)

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
    max_distance = max(edges.values())
    result = {
        j: min([max_distance] + [edges[i, j] for i in nodes if (i, j) in edges])
        for j in nodes[1:]
    }
    result[nodes[0]] = 0

    return result


def compute_min_distance_from(nodes, edges):
    max_distance = max(edges.values())
    result = {
        i: min([max_distance] + [edges[i, j] for j in nodes if (i, j) in edges])
        for i in nodes[:-1]
    }
    result[nodes[-1]] = 0

    return result


def generate_problem(n, nodes, edges, capacity, items, demand, blind=False):
    precedence_edges = compute_precedence(nodes, items, demand)
    (
        predecessors,
        successors,
        transitive_precedence_edges,
    ) = compute_predecessors_and_successors(nodes, precedence_edges)
    not_inferred_precedence_edges = compute_not_inferred_precedence(
        predecessors, successors, precedence_edges
    )
    filtered_edges = {
        (i, j): w
        for (i, j), w in edges.items()
        if w >= 0
        and i != j
        and check_edge(i, j, nodes, not_inferred_precedence_edges, capacity)
        and (j, i) not in transitive_precedence_edges
        and (
            (i, j) not in transitive_precedence_edges
            or (i, j) in not_inferred_precedence_edges
        )
    }
    total_demand = {i: sum(demand[i, j] for j in items) for i in nodes}
    min_distance_to = compute_min_distance_to(nodes, filtered_edges)
    min_distance_from = compute_min_distance_from(nodes, filtered_edges)

    output_lines = [
        "object_numbers:",
        "      customer: {}".format(n),
        "target:",
        "      unvisited: [ " + ", ".join([str(i) for i in range(1, n - 1)]) + " ]",
        "      location: 0",
        "      load: 0",
        "table_values:",
        "      capacity: {}".format(capacity),
        "      goal: {}".format(n - 1),
        "      demand: { "
        + ", ".join(["{}: {}".format(i - 1, total_demand[i]) for i in nodes])
        + " }",
        "      connected: { "
        + ", ".join("[{}, {}]: true".format(i - 1, j - 1) for i, j in filtered_edges)
        + " }",
        "      predecessors:",
        "            {",
    ]

    for i in nodes:
        output_lines.append(
            "                 {}: [ ".format(i - 1)
            + ", ".join(str(j - 1) for j in predecessors[i])
            + " ],"
        )

    output_lines.append("      }")

    if not blind:
        output_lines += [
            "      min_distance_to: { "
            + ", ".join("{}: {}".format(i - 1, min_distance_to[i]) for i in nodes)
            + " }",
            "      min_distance_from: { "
            + ", ".join("{}: {}".format(i - 1, min_distance_from[i]) for i in nodes)
            + " }",
        ]

    output_lines += [
        "      distance:",
        "            {",
    ]
    for i, j in filtered_edges:
        output_lines.append(
            "                  [{}, {}]: {},".format(i - 1, j - 1, filtered_edges[i, j])
        )
    output_lines.append("      }")

    return "\n".join(output_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--non-zero-base-case", action="store_true")
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()

    n, nodes, edges, capacity, m, items, demand, _ = read_tsplib.read_mpdtsp(args.input)
    problem = generate_problem(n, nodes, edges, capacity, items, demand, args.blind)

    with open("problem.yaml", "w") as f:
        f.write(problem)

    domain_file = (
        "domain_non_zero_base_blind.yaml"
        if args.non_zero_base_case and args.blind
        else "domain_non_zero_base.yaml"
        if args.non_zero_base_case
        else "domain_blind.yaml"
        if args.blind
        else "domain.yaml"
    )
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
        solution = [1]
        for transition in result["transitions"]:
            if transition["name"] == "visit":
                solution.append(transition["parameters"]["to"] + 1)
            if transition["name"] == "finish":
                solution.append(n)

        if args.non_zero_base_case:
            solution.append(n)

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_tsplib.validate_mpdtsp(
            solution, cost, nodes, edges, capacity, items, demand
        )
        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
