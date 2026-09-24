#!/usr/bin/env python3

import argparse
import os
import re
import resource
import subprocess
import time

import read_tsplib
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


def create_didp(n, nodes, edges, capacity, demand, k, blind=False):
    indices = {v: i for i, v in enumerate(nodes)}
    depot = nodes[0]
    matrix = [[edges.get((i, j), 0) for j in nodes] for i in nodes]
    problem = dict(
        object_numbers=dict(customer=n),
        target=dict(unvisited=list(range(1, n)), location=0, load=0, vehicles=1),
        table_values=dict(
            max_vehicles=k,
            capacity=capacity,
            demand={indices[i]: demand[i] for i in nodes},
            distance={(i, j): matrix[i][j] for i in range(n) for j in range(n)},
            mst_distance={
                (i, j): min(matrix[i][j], matrix[i][0] + matrix[0][j])
                for i in range(n)
                for j in range(n)
            },
            min_return=min((edges[i, depot] for i in nodes[1:]), default=0),
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
    parser.add_argument("--blind", action="store_true")
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
    problem = create_didp(n, nodes, edges, capacity, demand, k, blind=args.blind)

    with open("problem.yaml", "w") as f:
        f.write(problem)

    domain_file = "domain_blind.yaml" if args.blind else "domain.yaml"
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
        cost = round(result["cost"])
        solution = [depot]
        for transition in result["transitions"]:
            if transition["name"] == "visit-via-depot":
                solution.append(depot)
                solution.append(transition["parameters"]["to"] + 1)
            if transition["name"] == "visit":
                solution.append(transition["parameters"]["to"] + 1)

        solution.append(depot)

        print(solution)
        print(f"cost: {cost}")

        validation_result = read_tsplib.validate_cvrp(
            n, nodes, edges, capacity, demand, depot, solution, cost, k=k
        )
        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print(f"Execution time: {end - start}s")
