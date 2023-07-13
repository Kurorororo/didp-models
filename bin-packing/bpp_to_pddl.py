#! /usr/bin/env python3

import argparse
import os
import subprocess

import read_bpp


def generate_problem(name, n, c, weights):
    lines = [
        "(define (problem {})".format(name.replace(".", "_")),
        "    (:domain BPP)",
        "    (:objects",
        "        " + " ".join("item{}".format(j) for j in range(n)) + " - item)",
        "    (:init",
        "        (= (total-cost) 0)",
        "        (= (residual) 0)",
        "        (= (capacity) {})".format(c),
    ]
    for i in range(n):
        lines += ["        (= (weight item{}) {})".format(i, weights[i])]
    lines += ["    )", "    (:goal (and"]
    for i in range(n):
        lines += ["        (packed item{})".format(i)]
    lines += ["    ))", "    (:metric minimize (total-cost))", ")"]

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--planner-path", "-p", type=str)
    args = parser.parse_args()

    n, c, weights = read_bpp.read(args.input)
    name = os.path.basename(args.input)
    problem = generate_problem(name, n, c, weights)

    with open("problem.pddl", "w") as f:
        f.write(problem)

    if args.planner_path is not None:
        subprocess.run(
            [
                args.planner_path,
                "domain.pddl",
                "problem.pddl",
            ]
        )
