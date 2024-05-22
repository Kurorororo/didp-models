#! /usr/bin/env python3

import argparse
import os
import subprocess

import read_bpp


def generate_domain(number_of_tasks):
    lines = [
        "(define (domain BPP)",
        "    (:requirements :strips :typing :fluents :negative-preconditions)",
        "    (:types item)",
        "    (:constants "
        + " ".join("i{}".format(i) for i in range(1, number_of_tasks + 1))
        + " - item)",
        "    (:predicates (packed ?i - item))",
        "    (:functions (capacity) (residual) (bin-number) (weight ?i - item) (total-cost))",
    ]
    for i in range(1, number_of_tasks + 1):
        lines += [
            "    (:action pack-i{}".format(i),
            "        :parameters ()",
            "        :precondition (and (not (packed i{})) ".format(i)
            + "(<= (weight i{}) (residual))".format(i)
            + " (>= {} (bin-number)))".format(i),
            "        :effect (and (packed i{}) ".format(i)
            + "(decrease (residual) (weight i{}))".format(i)
            + " (increase (total-cost) 0))",
            "    )",
        ]
        lines += [
            "    (:action open-new-bin-and-pack-i{}".format(i),
            "        :parameters ()",
            "        :precondition (and (not (packed i{})) ".format(i)
            + "(> (weight i{}) (residual))".format(i)
            + " (>= {} (bin-number)))".format(i - 1),
            "        :effect (and (packed i{}) ".format(i)
            + " (assign (residual) (- (capacity) (weight i{})))".format(i)
            + " (increase (bin-number) 1)"
            + " (increase (total-cost) 1))",
            "    )",
        ]
    lines += [")"]

    return "\n".join(lines)


def generate_problem(name, n, c, weights):
    lines = [
        "(define (problem {})".format(name),
        "    (:domain BPP)",
        "    (:init",
        "        (= (total-cost) 0)",
        "        (= (residual) 0)",
        "        (= (bin-number) 0)",
        "        (= (capacity) {})".format(c),
    ]
    for i in range(n):
        lines += ["        (= (weight i{}) {})".format(i + 1, weights[i])]
    lines += ["    )", "    (:goal (and"]
    for i in range(n):
        lines += ["        (packed i{})".format(i + 1)]
    lines += ["    ))", "    (:metric minimize (total-cost))", ")"]

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--planner-path", "-p", type=str)
    args = parser.parse_args()

    n, c, weights = read_bpp.read(args.input)
    name = os.path.basename(args.input)
    domain = generate_domain(n)
    problem = generate_problem(name, n, c, weights)

    with open("domain.pddl", "w") as f:
        f.write(domain)

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
