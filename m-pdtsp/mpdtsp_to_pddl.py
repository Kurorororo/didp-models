#! /usr/bin/env python3

import argparse
import os
import subprocess

import read_tsplib
from mpdtsp_util import (
    check_edge,
    compute_not_inferred_precedence,
    compute_precedence,
    compute_predecessors_and_successors,
)


def generate_domain(nodes, predecessors, demand, capacity):
    lines = [
        "(define (domain mPDTSP)",
        "    (:requirements :strips :typing :fluents :negative-preconditions)",
        "    (:types customer)",
        "    (:constants " + " ".join(f"c{i}" for i in nodes) + " - customer)",
        "    (:predicates (connected ?c1 ?c2 - customer) (visited ?c - customer) (loc ?c - customer))",
        "    (:functions (total-cost) (load) (travel-cost ?c1 ?c2 - customer))",
    ]

    for i in nodes[1:-1]:
        lines += [
            f"    (:action visit-{i}",
            "        :parameters (?from - customer)",
            f"        :precondition (and (not (visited c{i})) (connected ?from c{i}) (loc ?from) (<= (+ (load) {demand[i]}) {capacity}) "
            + " ".join([f"(visited c{j})" for j in predecessors[i]])
            + ")",
            f"        :effect (and (not (loc ?from)) (loc c{i}) (visited c{i}) (increase (load) {demand[i]}) (increase (total-cost) (travel-cost ?from c{i})))",
            "    )",
        ]

    lines += [
        "    (:action return",
        "        :parameters (?from - customer)",
        f"        :precondition (and (connected ?from c{nodes[-1]}) (loc ?from) (forall (?c - customer) (visited ?c)))",
        f"        :effect (and (not (loc ?from)) (loc c{nodes[-1]}) (increase (total-cost) (travel-cost ?from c{nodes[-1]})))",
        "    )",
        ")",
    ]

    return "\n".join(lines)


def generate_problem(name, nodes, edges):
    output_lines = [
        f"(define (problem {name})",
        "    (:domain mPDTSP)",
        "    (:init",
        "        (= (total-cost) 0)",
        f"        (loc c{nodes[0]})",
        "        (= (load) 0)",
        f"        (visited c{nodes[0]})",
        f"        (visited c{nodes[-1]})",
    ]

    for i in nodes:
        for j in nodes:
            if (i, j) in edges:
                output_lines += [
                    f"        (connected c{i} c{j})",
                    f"        (= (travel-cost c{i} c{j}) {edges[i, j]})",
                ]

    output_lines += [
        "    )",
        "    (:goal (and",
        f"        (loc c{nodes[-1]})",
    ]

    for i in nodes:
        output_lines += [f"        (visited c{i})"]

    output_lines += ["        )", "    )", "    (:metric minimize total-cost)", ")"]

    return "\n".join(output_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--planner-path", "-p", type=str)
    args = parser.parse_args()

    name = os.path.basename(args.input)
    n, nodes, edges, capacity, m, items, demand, _ = read_tsplib.read_mpdtsp(args.input)

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

    domain = generate_domain(nodes, predecessors, total_demand, capacity)
    problem = generate_problem(name, nodes, filtered_edges)

    with open("domain.pddl", "w") as f:
        f.write(domain)

    with open("problem.pddl", "w") as f:
        f.write(problem)

    if args.planner_path is not None:
        subprocess.run([args.planner_path, "domain.pddl", "problem.pddl", "plan.txt"])
