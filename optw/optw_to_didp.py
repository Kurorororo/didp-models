#!/usr/bin/env python3

import argparse
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
    blind=False,
):
    shortest_distance = compute_shortest_distance(distance, service_time)

    min_distance_from = [
        min(service_time[i] + distance[i][j] for j in vertices if i != j)
        for i in vertices
    ]
    efficiency_from = [p / c + epsilon for p, c in zip(profit, min_distance_from)]

    min_distance_to = [
        min(service_time[i] + distance[i][j] for i in vertices if i != j)
        for j in vertices
    ]
    efficiency_to = [p / c + epsilon for p, c in zip(profit, min_distance_to)]

    output_lines = [
        "object_numbers:",
        "  node: {}".format(len(vertices)),
        "target:",
        "  unvisited: [ " + ", ".join([str(i) for i in vertices[1:]]) + " ]",
        "  location: 0",
        "  time: 0",
        "table_values:",
        "  profit: { "
        + ", ".join(["{}: {}".format(i, profit[i]) for i in vertices])
        + " }",
        "  opening: { "
        + ", ".join(["{}: {}".format(i, opening[i]) for i in vertices])
        + " }",
        "  closing: { "
        + ", ".join(["{}: {}".format(i, closing[i]) for i in vertices])
        + " }",
        "  min_distance_from: { "
        + ", ".join(["{}: {}".format(i, min_distance_from[i]) for i in vertices])
        + " }",
        "  min_distance_to: { "
        + ", ".join(["{}: {}".format(i, min_distance_to[i]) for i in vertices])
        + " }",
        "  efficiency_from: { "
        + ", ".join(["{}: {}".format(i, efficiency_from[i]) for i in vertices])
        + " }",
        "  efficiency_to: { "
        + ", ".join(["{}: {}".format(i, efficiency_to[i]) for i in vertices])
        + " }",
        "  distance:",
        "    {",
    ]

    for i in vertices:
        for j in vertices:
            output_lines.append(
                "      [{}, {}]: {},".format(i, j, service_time[i] + distance[i][j])
            )

    output_lines.append("    }")
    output_lines += [
        "  shortest_distance:",
        "    {",
    ]

    for i in vertices:
        for j in vertices:
            output_lines.append(
                "      [{}, {}]: {},".format(i, j, shortest_distance[i][j])
            )

    output_lines.append("    }")

    output_lines += [
        "  shortest_return_distance:",
        "    {",
    ]

    for i in vertices:
        for j in vertices:
            output_lines.append(
                "      [{}, {}]: {},".format(
                    i,
                    j,
                    shortest_distance[i][j] + shortest_distance[j][0],
                )
            )

    output_lines.append("    }")

    output_lines += [
        "  distance_plus_shortest_return:",
        "    {",
    ]

    for i in vertices:
        for j in vertices:
            output_lines.append(
                "      [{}, {}]: {},".format(
                    i,
                    j,
                    service_time[i] + distance[i][j] + shortest_distance[j][0],
                )
            )

    output_lines.append("    }")

    if not blind:
        output_lines += [
            "dual_bounds:",
            "  - >",
        ]

        for i, v in enumerate(vertices[1:]):
            line = "    "

            if i < len(vertices[1:]) - 1 and len(vertices[1:]) > 1:
                line += "(+ "

            if i == len(vertices[1:]) - 1:
                line += "   "

            line += "(if (and (is_in {} unvisited) (and (<= (+ time (shortest_distance location {})) {}) (<= (+ time (shortest_return_distance location {})) {}))) {} 0)".format(
                v, v, closing[v], v, closing[0], profit[v]
            )

            if i == len(vertices[1:]) - 1:
                line += ")" * (len(vertices[1:]) - 1)

            output_lines.append(line)

        output_lines += [
            "  - >",
            "    (floor (* (- (- {} time) (min_distance_from location))".format(
                closing[0]
            ),
        ]

        for i, v in enumerate(vertices[1:]):
            line = "              "

            if i < len(vertices[1:]) - 1 and len(vertices[1:]) > 1:
                line += "(max "

            if i == len(vertices[1:]) - 1:
                line += "     "

            line += "(if (and (is_in {} unvisited) (and (<= (+ time (shortest_distance location {})) {}) (<= (+ time (shortest_return_distance location {})) {}))) {} 0)".format(
                v, v, closing[v], v, closing[0], efficiency_from[v]
            )

            if i == len(vertices[1:]) - 1:
                line += ")" * (len(vertices[1:]) - 1) + "))"

            output_lines.append(line)

        output_lines += [
            "  - >",
            "    (floor (* (- (- {} time) {})".format(closing[0], min_distance_to[0]),
        ]

        for i, v in enumerate(vertices[1:]):
            line = "              "

            if i < len(vertices[1:]) - 1 and len(vertices[1:]) > 1:
                line += "(max "

            if i == len(vertices[1:]) - 1:
                line += "     "

            line += "(if (and (is_in {} unvisited) (and (<= (+ time (shortest_distance location {})) {}) (<= (+ time (shortest_return_distance location {})) {}))) {} 0)".format(
                v, v, closing[v], v, closing[0], efficiency_to[v]
            )

            if i == len(vertices[1:]) - 1:
                line += ")" * (len(vertices[1:]) - 1) + "))"

            output_lines.append(line)

    output_lines += []

    return "\n".join(output_lines)


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
        blind=args.blind,
    )

    with open("problem.yaml", "w") as f:
        f.write(dypdl_text)

    domain_file = "domain.yaml"
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
        cost = result["cost"]
        solution = [0]
        for transition in result["transitions"]:
            if transition["name"] == "visit":
                solution.append(transition["parameters"]["to"])

        solution.append(0)

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_optw.validate_optw(
            service_time, profit, opening, closing, distance, solution, cost
        )

        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
