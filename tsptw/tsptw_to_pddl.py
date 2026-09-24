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
        f"(define (problem {name})",
        "    (:domain TSPTW)",
        "    (:objects",
    ]

    output_lines += ["        depot0 - depot"]
    output_lines += [
        "        " + " ".join([f"customer{c}" for c in nodes if c > 0]) + " - customer)"
    ]
    output_lines += [
        "    (:init",
        "        (loc depot0)",
        "        (= (time) 0)",
    ]

    for i in nodes[1:]:
        output_lines += [
            f"        (= (ready-time customer{i}) {a[i]})",
            f"        (= (due-date customer{i}) {b[i]})",
        ]

    for i in nodes:
        if i == 0:
            output_lines += [
                f"        (= (travel-cost depot0 customer{j}) {edges[0, j]})"
                for j in nodes
                if j > 0
            ]
        else:
            output_lines += [
                f"        (= (travel-cost customer{i} depot0) {edges[i, 0]})"
            ]
            for j in nodes[1:]:
                if i != j:
                    output_lines += [
                        f"        (= (travel-cost customer{i} customer{j}) {edges[i, j]})"
                    ]

    if redundant_constraints:
        shortest_distance = compute_shortest_distance(nodes, edges)

        for i in nodes:
            if i == 0:
                output_lines += [
                    f"        (= (shortest-cost depot0 customer{j}) {shortest_distance[0, j]})"
                    for j in nodes
                    if j > 0
                ]
            else:
                output_lines += [
                    f"        (= (shortest-cost customer{i} depot0) {shortest_distance[i, 0]})"
                ]
                for j in nodes[1:]:
                    if i != j:
                        output_lines += [
                            f"        (= (shortest-cost customer{i} customer{j}) {shortest_distance[i, j]})"
                        ]

    output_lines += ["        (= total-cost 0))"]

    output_lines += ["    (:goal", "        (and"]
    output_lines += ["         (loc depot0)"]

    for i in nodes[1:]:
        output_lines += [f"            (visited customer{i})"]

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
