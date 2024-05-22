#!/usr/bin/env python3

import argparse
import os
import re
import resource
import subprocess
import time

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


def create_picat_input(n, k, capacity, nodes, edges, demand):
    lines = [
        str(n),
        str(k),
        str(capacity),
    ]

    for i in nodes:
        line = []
        for j in nodes:
            if (i, j) in edges:
                line.append(str(edges[i, j]))
            else:
                line.append("0")

        lines.append(" ".join(line))

    for i in nodes:
        lines.append(str(demand[i]))

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--picat-path", "-p", type=str)
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

    problem = create_picat_input(n, k, capacity, nodes, edges, demand)

    with open("problem.txt", "w") as f:
        f.write(problem)

    if args.picat_path:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        dirname = os.path.dirname(__file__)
        subprocess.run(
            [args.picat_path, os.path.join(dirname, "cvrp_bb.pi"), "problem.txt"],
            preexec_fn=fn,
        )

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
