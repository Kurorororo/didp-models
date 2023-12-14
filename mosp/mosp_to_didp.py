#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_mosp
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


def create_didp(problem_name, item_to_patterns, pattern_to_items):
    m = len(item_to_patterns)
    item_to_neighbors = read_mosp.compute_item_to_neighbors(
        item_to_patterns, pattern_to_items
    )

    output_lines = [
        "problem: {}".format(problem_name),
        "object_numbers:",
        "      item: {}".format(m),
        "target:",
        "      remaining: [ " + ", ".join(str(i) for i in range(m)) + " ]",
        "      opened: []",
        "table_values:",
        "      neighbors: {",
    ]
    for i in range(m):
        output_lines.append(
            "                  {}: [ ".format(i)
            + ", ".join(str(j) for j in item_to_neighbors[i])
            + " ],"
        )
    output_lines.append("            }")

    return "\n".join(output_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    args = parser.parse_args()

    item_to_patterns, pattern_to_items = read_mosp.read(args.input)
    name = os.path.basename(args.input)
    problem = create_didp(name, item_to_patterns, pattern_to_items)

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
        item_order = []
        for transition in result["transitions"]:
            item_order.append(transition["parameters"]["c"])
        solution = read_mosp.item_order_to_pattern_order(item_to_patterns, item_order)

        print(solution)

        if cost is not None:
            print("cost: {}".format(cost))

            validation_result = read_mosp.validate(
                item_to_patterns, pattern_to_items, solution, cost
            )

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
