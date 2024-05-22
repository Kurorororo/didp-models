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


def create_picat_input(
    vertices,
    service_time,
    profit,
    opening,
    closing,
    distance,
):
    lines = [str(len(vertices))]

    for i in vertices:
        lines.append(
            "{} {} {}".format(
                profit[i],
                opening[i],
                closing[i],
            )
        )

    for i in vertices:
        line = []
        for j in vertices:
            line.append(str(service_time[i] + distance[i][j]))
        lines.append(" ".join(line))

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--round-to-second", action="store_true")
    parser.add_argument("--picat-path", "-p", type=str)
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

    problem = create_picat_input(
        vertices,
        service_time,
        profit,
        opening,
        closing,
        distance,
    )

    with open("problem.txt", "w") as f:
        f.write(problem)

    if args.picat_path is not None:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        dirname = os.path.dirname(__file__)
        print("Preprocessing time: {}s".format(time.perf_counter() - start))
        subprocess.run(
            [args.picat_path, os.path.join(dirname, "optw"), "problem.txt"],
            preexec_fn=fn,
        )

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
