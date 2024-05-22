#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_tsplib
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


def create_picat_input(n, nodes, edges, capacity, items, demand):
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

    lines = [str(n), str(capacity), str(len(filtered_edges))]

    for i, j in filtered_edges:
        lines.append("{} {} {}".format(i, j, filtered_edges[i, j]))

    for i in nodes:
        lines.append(str(total_demand[i]))

    lines.append(str(sum(len(predecessors[i]) for i in nodes)))

    for i in nodes:
        for j in predecessors[i]:
            lines.append("{} {}".format(j, i))

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--picat-path", "-p", type=str)
    args = parser.parse_args()

    n, nodes, edges, capacity, m, items, demand, _ = read_tsplib.read_mpdtsp(args.input)
    problem = create_picat_input(n, nodes, edges, capacity, items, demand)

    with open("problem.txt", "w") as f:
        f.write(problem)

    if args.picat_path:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        dirname = os.path.dirname(__file__)
        subprocess.run(
            [args.picat_path, os.path.join(dirname, "mpdtsp_bb.pi"), "problem.txt"],
            preexec_fn=fn,
        )

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
