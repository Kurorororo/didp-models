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
        + " ".join(f"i{i}" for i in range(1, number_of_tasks + 1))
        + " - item)",
        "    (:predicates (packed ?i - item))",
        "    (:functions (capacity) (residual) (bin-number) (weight ?i - item) (total-cost))",
    ]
    for i in range(1, number_of_tasks + 1):
        lines += [
            f"    (:action pack-i{i}",
            "        :parameters ()",
            f"        :precondition (and (not (packed i{i})) "
            + f"(<= (weight i{i}) (residual))"
            + f" (>= {i} (bin-number)))",
            f"        :effect (and (packed i{i}) "
            + f"(decrease (residual) (weight i{i}))"
            + " (increase (total-cost) 0))",
            "    )",
        ]
        lines += [
            f"    (:action open-new-bin-and-pack-i{i}",
            "        :parameters ()",
            f"        :precondition (and (not (packed i{i})) "
            + f"(> (weight i{i}) (residual))"
            + f" (>= {i - 1} (bin-number)))",
            f"        :effect (and (packed i{i}) "
            + f" (assign (residual) (- (capacity) (weight i{i})))"
            + " (increase (bin-number) 1)"
            + " (increase (total-cost) 1))",
            "    )",
        ]
    lines += [")"]

    return "\n".join(lines)


def generate_problem(name, n, c, weights):
    lines = [
        f"(define (problem {name})",
        "    (:domain BPP)",
        "    (:init",
        "        (= (total-cost) 0)",
        "        (= (residual) 0)",
        "        (= (bin-number) 0)",
        f"        (= (capacity) {c})",
    ]
    for i in range(n):
        lines += [f"        (= (weight i{i + 1}) {weights[i]})"]
    lines += ["    )", "    (:goal (and"]
    for i in range(n):
        lines += [f"        (packed i{i + 1})"]
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
