#! /usr/bin/env python3

import argparse
import os
import subprocess

import read_mosp


def create_strips(problem_name, item_to_patterns, pattern_to_items):
    n_items = len(item_to_patterns)
    n_patterns = len(pattern_to_items)
    domain = [
        "(define (domain openstacks-sequencedstrips-nonADL-{})".format(problem_name),
        "    (:requirements :typing :negative-preconditions :action-costs)",
        "    (:types item pattern count)",
        "    (:constants",
        "        " + " ".join(["i{}".format(i) for i in range(n_items)]) + " - item",
        "        "
        + " ".join(["p{}".format(j) for j in range(n_patterns)])
        + " - pattern",
        "    )",
        "",
        "    (:predicates",
        "        (waiting ?i - item)",
        "        (started ?i - item)",
        "        (finished ?i - item)",
        "        (processed ?p - pattern)",
        "        (stacks-avail ?s - count)",
        "        (next-count ?s ?ns - count)",
        "     )",
        "",
        "    (:functions (total-cost))",
        "",
        "    (:action open-new-stack",
        "        :parameters (?open ?new-open - count)",
        "        :precondition (and (stacks-avail ?open)(next-count ?open ?new-open))",
        "        :effect (and (not (stacks-avail ?open))(stacks-avail ?new-open)"
        + " (increase (total-cost) 1))",
        "     )",
        "",
        "    (:action start-item",
        "        :parameters (?i - item ?avail ?new-avail - count)",
        "        :precondition (and (waiting ?i) (stacks-avail ?avail)"
        + " (next-count ?new-avail ?avail))",
        "        :effect (and (not (waiting ?i)) (started ?i) (not (stacks-avail ?avail))"
        + " (stacks-avail ?new-avail))",
        "     )",
    ]

    for j in range(n_patterns):
        precondition = "        :precondition (and (not (processed p{}))".format(j)
        precondition += " ".join(
            ["(started i{})".format(i) for i in pattern_to_items[j]]
        )
        precondition += ")"
        domain += [
            "",
            "    (:action process-pattern-p{}".format(j),
            "        :parameters ()",
            precondition,
            "        :effect (and (processed p{}))".format(j),
            "    )",
        ]

    for i in range(n_items):
        precondition = "        :precondition (and (started i{})".format(i)
        precondition += " ".join(
            ["(processed p{})".format(j) for j in item_to_patterns[i]]
        )
        precondition += "(stacks-avail ?avail)(next-count ?avail ?new-avail))"
        domain += [
            "",
            "    (:action finish-item-i{}".format(i),
            "        :parameters (?avail ?new-avail - count)",
            precondition,
            "        :effect (and (not (started i{})) (finished i{})".format(i, i)
            + " (not (stacks-avail ?avail)) (stacks-avail ?new-avail)))",
        ]
    domain += ["    )"]

    problem = [
        "(define (problem {})".format(problem_name),
        "    (:domain openstacks-sequencedstrips-nonADL-{})".format(problem_name),
        "",
        "    (:objects",
        "        "
        + " ".join(["n{}".format(c) for c in range(n_items + 1)])
        + " - count",
        "    )",
        "",
        "    (:init",
        "        "
        + " ".join(["(next-count n{} n{})".format(c, c + 1) for c in range(n_items)]),
        "        (stacks-avail n0)",
    ]

    for i in range(n_items):
        problem += ["        (waiting i{})".format(i)]

    problem += ["        (= (total-cost) 0)", "", ")", "", "(:goal", "    (and"]

    for i in range(n_items):
        problem += ["        (finished i{})".format(i)]

    problem += ["    ))", "", "    (:metric minimize (total-cost))", "", ")"]

    return "\n".join(domain), "\n".join(problem)


def create_numeric(problem_name, item_to_patterns, pattern_to_items):
    n_items = len(item_to_patterns)
    n_patterns = len(pattern_to_items)
    domain = [
        "(define (domain openstacks-numeric-{})".format(problem_name),
        "(:requirements :typing :negative-preconditions :numeric-fluents "
        + " :action-costs)",
        "(:types item pattern)",
        "(:constants",
        " ".join(["i{}".format(i) for i in range(n_items)]) + " - item",
        " ".join(["p{}".format(j) for j in range(n_patterns)]) + " - pattern",
        ")",
        "",
        "(:predicates",
        "   (waiting ?i - item)",
        "   (started ?i - item)",
        "   (finished ?i - item)",
        "   (processed ?p - pattern)",
        ")",
        "",
        "(:functions (stacks) (opened))",
        "",
        "(:action open-new-stack",
        ":parameters ()",
        ":precondition ()",
        ":effect (and (increase (stacks) 1) (increase (opened) 1))",
        ")",
        "",
        "(:action start-item",
        ":parameters (?i - item)",
        ":precondition (and (waiting ?i) (<= (stacks) 1))",
        ":effect (and (not (waiting ?i))(started ?i)(decrease (stacks) 1))",
        ")",
    ]

    for j in range(n_patterns):
        precondition = ":precondition (and (not (processed p{}))".format(j)
        precondition += "".join(
            ["(started i{})".format(i) for i in pattern_to_items[j]]
        )
        precondition += ")"
        domain += [
            "",
            "(:action process-pattern-p{}".format(j),
            ":parameters ()",
            precondition,
            ":effect (and (processed p{}))".format(j),
            ")",
        ]

    for i in range(n_items):
        precondition = ":precondition (and (started i{})".format(i)
        precondition += "".join(
            ["(processed p{})".format(j) for j in item_to_patterns[i]]
        )
        precondition += ")"
        domain += [
            "",
            "(:action finish-item-i{}".format(i),
            ":parameters ()",
            precondition,
            ":effect (and (not (started i{})) (finished i{})".format(i, i)
            + " (increase (stacks) 1)))",
        ]
    domain += [")"]

    problem = [
        "(define (problem {})".format(problem_name),
        "(:domain openstacks-numeric-{})".format(problem_name),
        "",
        "(:init",
        "(= (stacks) 0)",
    ]

    for i in range(n_items):
        problem += ["", "(waiting i{})".format(i)]

    problem += ["", "(= (total-cost) 0)", "", ")", "", "(:goal", "(and"]

    for i in range(n_items):
        problem += ["(finished i{})".format(i)]

    problem += ["))", "", "(:metric minimize (opened))", "", ")"]

    return "\n".join(domain), "\n".join(problem)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--planner-path", "-p", type=str)
    parser.add_argument("--numeric", "-n", action="store_true")
    args = parser.parse_args()

    item_to_patterns, pattern_to_items = read_mosp.read(args.input)
    name = os.path.basename(args.input)

    if args.numeric:
        domain, problem = create_numeric(name, item_to_patterns, pattern_to_items)
    else:
        domain, problem = create_strips(name, item_to_patterns, pattern_to_items)

    with open("domain.pddl", "w") as f:
        f.write(domain)

    with open("problem.pddl", "w") as f:
        f.write(problem)

    if args.planner_path is not None:
        subprocess.run([args.planner_path, "domain.pddl", "problem.pddl", "plan.txt"])
