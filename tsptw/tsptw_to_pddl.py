#!/usr/bin/env python3

import argparse
import os
import subprocess

import read_tsptw


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


def create_pddl(name, nodes, edges, a, b, redundant_constraints):
    output_lines = [
        "(define (problem {})".format(name),
        "    (:domain TSPTW)",
        "    (:objects",
    ]

    output_lines += ["        depot0 - depot"]
    output_lines += [
        "        "
        + " ".join(["customer{}".format(c) for c in nodes if c > 0])
        + " - customer)"
    ]
    output_lines += [
        "    (:init",
        "        (loc depot0)",
        "        (= (time) 0)",
    ]

    for i in nodes[1:]:
        output_lines += [
            "        (= (ready-time customer{}) {})".format(i, a[i]),
            "        (= (due-date customer{}) {})".format(i, b[i]),
        ]

    for i in nodes:
        if i == 0:
            output_lines += [
                "        (= (travel-cost depot0 customer{}) {})".format(j, edges[0, j])
                for j in nodes
                if j > 0
            ]
        else:
            output_lines += [
                "        (= (travel-cost customer{} depot0) {})".format(i, edges[i, 0])
            ]
            for j in nodes[1:]:
                if i != j:
                    output_lines += [
                        "        (= (travel-cost customer{} customer{}) {})".format(
                            i, j, edges[i, j]
                        )
                    ]

    if redundant_constraints:
        shortest_distance = compute_shortest_distance(nodes, edges)

        for i in nodes:
            if i == 0:
                output_lines += [
                    "        (= (shortest-cost depot0 customer{}) {})".format(
                        j, shortest_distance[0, j]
                    )
                    for j in nodes
                    if j > 0
                ]
            else:
                output_lines += [
                    "        (= (shortest-cost customer{} depot0) {})".format(
                        i, shortest_distance[i, 0]
                    )
                ]
                for j in nodes[1:]:
                    if i != j:
                        output_lines += [
                            "        (= (shortest-cost customer{} customer{}) {})".format(
                                i, j, shortest_distance[i, j]
                            )
                        ]

    output_lines += ["        (= total-cost 0))"]

    output_lines += ["    (:goal", "        (and"]
    output_lines += ["         (loc depot0)"]

    for i in nodes[1:]:
        output_lines += ["            (visited customer{})".format(i)]

    output_lines += ["        ))", "    (:metric minimize total-cost))"]

    return "\n".join(output_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--planner-path", "-p", type=str)
    parser.add_argument("--redundant-constraints", "-r", action="store_true")
    args = parser.parse_args()

    n, nodes, edges, a, b = read_tsptw.read(args.input)
    name = os.path.basename(args.input)
    pddl_text = create_pddl(name, nodes, edges, a, b, args.redundant_constraints)

    with open("problem.pddl", "w") as f:
        f.write(pddl_text)

    if args.redundant_constraints:
        domain_path = os.path.join(os.path.dirname(__file__), "domain-redundant.pddl")
    else:
        domain_path = os.path.join(os.path.dirname(__file__), "domain.pddl")

    if args.planner_path is not None:
        subprocess.run([args.planner_path, domain_path, "problem.pddl", "plan.txt"])
