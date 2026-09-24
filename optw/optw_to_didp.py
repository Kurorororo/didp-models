#!/usr/bin/env python3

import argparse
import math
import os
import resource
import subprocess
import time

import read_optw
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


def compute_shortest_distance(distance, service_time):
    vertices = list(range(len(distance)))
    shortest_distance = [
        [service_time[i] + distance[i][j] for j in vertices] for i in vertices
    ]

    for k in vertices:
        if k == 0:
            continue

        for i in vertices:
            if k == i:
                continue
            for j in vertices:
                if k == j or i == j:
                    continue

                d = shortest_distance[i][k] + shortest_distance[k][j]

                if shortest_distance[i][j] > d:
                    shortest_distance[i][j] = d

    return shortest_distance


def create_didp(
    vertices,
    service_time,
    profit,
    opening,
    closing,
    distance,
    epsilon=1e-6,
):
    if not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("epsilon must be finite and nonnegative")
    goal = len(vertices)
    shortest = compute_shortest_distance(distance, service_time)
    travel = [[service_time[i] + distance[i][j] for j in vertices] for i in vertices]
    min_from = [
        min((travel[i][j] for j in vertices if i != j), default=0) for i in vertices
    ]
    min_to = [
        min((travel[i][j] for i in vertices if i != j), default=0) for j in vertices
    ]
    initial_time = max(0, opening[0])
    reachable = [
        i
        for i in vertices[1:]
        if max(initial_time + shortest[0][i], opening[i])
        <= min(closing[i], closing[0] - shortest[i][0])
    ]
    values = dict(
        goal=goal,
        epsilon=epsilon,
        profit=dict(enumerate(profit + [0])),
        reward=dict(enumerate([max(0, p) for p in profit] + [0])),
        opening=dict(enumerate(opening + [0])),
        closing=dict(enumerate(closing + [closing[0]])),
        min_from=dict(enumerate(min_from + [0])),
        min_to=dict(enumerate(min_to + [0])),
        shortest_return=dict(enumerate([shortest[i][0] for i in vertices] + [0])),
        travel={
            (i, j): travel[i][j] if i < goal and j < goal else 0
            for i in range(goal + 1)
            for j in range(goal + 1)
        },
        shortest={
            (i, j): shortest[i][j] if i < goal and j < goal else 0
            for i in range(goal + 1)
            for j in range(goal + 1)
        },
    )
    problem = dict(
        object_numbers=dict(node=goal + 1),
        target=dict(reachable=reachable, location=0, time=initial_time),
        table_values=values,
    )
    return yaml.safe_dump(problem, sort_keys=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--round-to-second", action="store_true")
    parser.add_argument("--epsilon", type=float, default=1e-6)
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()

    vertices, service_time, profit, opening, closing, distance = read_optw.read_optw(
        args.input
    )

    if args.round_to_second:
        service_time, opening, closing, distance = read_optw.round_to_second(
            service_time, opening, closing, distance
        )
    else:
        service_time, opening, closing, distance = read_optw.round_to_first(
            service_time, opening, closing, distance
        )

    dypdl_text = create_didp(
        vertices,
        service_time,
        profit,
        opening,
        closing,
        distance,
        epsilon=args.epsilon,
    )

    with open("problem.yaml", "w") as f:
        f.write(dypdl_text)

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
        cost = result["cost"]
        solution = [0]
        for transition in result["transitions"]:
            if transition["name"] == "visit":
                solution.append(transition["parameters"]["to"])

        solution.append(0)

        print(solution)
        print(f"cost: {cost}")

        validation_result = read_optw.validate_optw(
            service_time, profit, opening, closing, distance, solution, cost
        )

        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print(f"Execution time: {end - start}s")
