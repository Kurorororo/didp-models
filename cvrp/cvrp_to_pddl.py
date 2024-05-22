#!/usr/bin/env python3

import argparse
import os
import re
import subprocess

import read_tsplib


def generate_problem(name, nodes, edges, capacity, demand, depot, k):
    output_lines = [
        "(define (problem {})".format(name),
        "    (:domain CVRP)",
        "    (:objects",
        "        "
        + " ".join(["c{}".format(c) for c in nodes if c != depot])
        + " - customer)",
        "    (:init",
        "        (= (total-cost) 0)",
        "        (loc d1)",
        "        (= (load) 0)",
        "        (= (vehicles) 1)",
        "        (= (max_vehicles) {})".format(k),
        "        (= (capacity) {})".format(capacity),
    ]

    for i in nodes:
        if i != depot:
            output_lines.append("        (= (demand c{}) {})".format(i, demand[i]))

    for i in nodes:
        c_i = "d1" if i == depot else "c{}".format(i)
        for j in nodes:
            if i == j:
                continue
            c_j = "d1" if j == depot else "c{}".format(j)
            if (i, j) in edges:
                output_lines.append(
                    "        (= (travel-cost {} {}) {})".format(c_i, c_j, edges[i, j])
                )

    for i in nodes:
        if i == depot:
            continue
        for j in nodes:
            if i == j or j == depot:
                continue
            if (i, j) in edges:
                output_lines.append(
                    "        (= (travel-cost-via-depot c{} c{}) {})".format(
                        i, j, edges[i, depot] + edges[depot, j]
                    )
                )

    output_lines += ["    )", "    (:goal", "         (and", "             (loc d1)"]

    for i in nodes:
        if i != depot:
            output_lines += ["             (visited c{})".format(i)]

    output_lines += ["        )", "    )", "    (:metric minimize total-cost)", ")"]

    return "\n".join(output_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--planner-path", "-p", type=str)
    args = parser.parse_args()

    name = os.path.basename(args.input)
    m = re.match(r".+k(\d+).+", name)
    k = int(m.group(1))

    (
        _,
        nodes,
        edges,
        capacity,
        demand,
        depot,
        _,
    ) = read_tsplib.read_cvrp(args.input)
    problem = generate_problem(name, nodes, edges, capacity, demand, depot, k)

    with open("problem.pddl", "w") as f:
        f.write(problem)

    domain_path = os.path.join(os.path.dirname(__file__), "domain.pddl")

    if args.planner_path is not None:
        subprocess.run([args.planner_path, domain_path, "problem.pddl", "plan.txt"])
