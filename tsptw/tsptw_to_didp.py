#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_tsptw
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


def compute_shortest_distance(nodes, edges):
    shortest_distance = {k: v for k, v in edges.items()}

    for k in nodes:
        if k == 0:
            continue

        for i in nodes:
            if k == i:
                continue
            for j in nodes:
                if k == j or i == j:
                    continue

                d = shortest_distance[i, k] + shortest_distance[k, j]

                if shortest_distance[i, j] > d:
                    shortest_distance[i, j] = d

    return shortest_distance


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


def create_didp(n, nodes, edges, a, b, use_bound=True):
    shortest_distance = compute_shortest_distance(nodes, edges)
    output_lines = [
        "object_numbers:",
        f"      customer: {n}",
        "target:",
        "      unvisited: [ " + ", ".join([str(i) for i in range(1, n)]) + " ]",
        "      location: 0",
        f"      time: {max(0, a[0])}",
        "table_values:",
        "      ready_time: { " + ", ".join([f"{i}: {a[i]}" for i in nodes]) + " }",
        "      due_date: { " + ", ".join([f"{i}: {b[i]}" for i in nodes]) + " }",
        "      distance:",
        "            {",
    ]
    for i, j in edges:
        output_lines.append(f"                  [{i}, {j}]: {edges[i, j]},")
    output_lines.append("      }")
    output_lines += [
        "      shortest_distance:",
        "            {",
    ]
    for i, j in edges:
        output_lines.append(f"                  [{i}, {j}]: {shortest_distance[i, j]},")
    output_lines.append("      }")

    if use_bound:
        min_distance_to = compute_min_distance_to(nodes, edges)
        min_distance_from = compute_min_distance_from(nodes, edges)
        output_lines += [
            "      min_distance_to: { "
            + ", ".join(f"{i}: {min_distance_to[i]}" for i in nodes)
            + " }",
            "      min_distance_from: { "
            + ", ".join(f"{i}: {min_distance_from[i]}" for i in nodes)
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
    parser.add_argument("--mst", action="store_true")
    parser.add_argument("--makespan", action="store_true")
    args = parser.parse_args()

    n, nodes, edges, a, b = read_tsptw.read(args.input)
    dypdl_text = create_didp(n, nodes, edges, a, b)

    with open("problem.yaml", "w") as f:
        f.write(dypdl_text)

    domain_file = (
        ("domain_makespan_mst.yaml" if args.mst else "domain_makespan.yaml")
        if args.makespan
        else ("domain_mst.yaml" if args.mst else "domain.yaml")
    )
    domain_path = os.path.join(os.path.dirname(__file__), domain_file)

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
        cost = result["cost"]
        solution = [0]
        for transition in result["transitions"]:
            if transition["name"] == "visit":
                solution.append(transition["parameters"]["to"])

        solution.append(0)

        print(solution)
        print(f"cost: {cost}")

        validation_result = read_tsptw.validate(
            n, edges, a, b, solution, cost, makespan=args.makespan
        )

        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print(f"Execution time: {end - start}s")
