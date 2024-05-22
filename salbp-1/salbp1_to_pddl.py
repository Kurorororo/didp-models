#! /usr/bin/env python3

import argparse
import os
import subprocess

import read_salbp1


def generate_domain(number_of_tasks, predecessors, separate_open_station=False):
    lines = [
        "(define (domain SALBP1)",
        "    (:requirements :strips :typing :fluents :negative-preconditions)",
        "    (:types task)",
        "    (:constants "
        + " ".join("t{}".format(i) for i in range(1, number_of_tasks + 1))
        + " - task)",
        "    (:predicates (completed ?t - task))",
        "    (:functions (cycle-time) (idle-time) (time ?t - task) (total-cost))",
    ]
    if separate_open_station:
        lines += [
            "    (:action open-station",
            "        :parameters ()",
            "        :precondition ()",
            "        :effect (and (assign (idle-time) (cycle-time))"
            + " (increase (total-cost) 1))",
            "    )",
        ]
    for i in range(1, number_of_tasks + 1):
        lines += [
            "    (:action do-t{}".format(i),
            "        :parameters ()",
            "        :precondition (and (not (completed t{})) ".format(i)
            + "(<= (time t{}) (idle-time))".format(i)
            + " ".join("(completed t{})".format(j) for j in predecessors[i])
            + ")",
            "        :effect (and (completed t{}) ".format(i)
            + "(decrease (idle-time) (time t{}))".format(i)
            + " (increase (total-cost) 0))",
            "    )",
        ]
        if not separate_open_station:
            lines += [
                "    (:action open-station-and-do-t{}".format(i),
                "        :parameters ()",
                "        :precondition (and (not (completed t{})) ".format(i)
                + "(> (time t{}) (idle-time))".format(i)
                + " ".join("(completed t{})".format(j) for j in predecessors[i])
                + ")",
                "        :effect (and (completed t{}) ".format(i)
                + " (assign (idle-time) (- (cycle-time) (time t{})))".format(i)
                + " (increase (total-cost) 1))",
                "    )",
            ]
    lines += [")"]

    return "\n".join(lines)


def generate_problem(name, number_of_tasks, cycle_time, task_times):
    lines = [
        "(define (problem {})".format(name),
        "    (:domain SALBP1)",
        "    (:init",
        "        (= (total-cost) 0)",
        "        (= (idle-time) 0)",
        "        (= (cycle-time) {})".format(cycle_time),
    ]
    for i in range(1, number_of_tasks + 1):
        lines += ["        (= (time t{}) {})".format(i, task_times[i])]
    lines += ["    )", "    (:goal (and"]
    for i in range(1, number_of_tasks + 1):
        lines += ["        (completed t{})".format(i)]
    lines += ["    ))", "    (:metric minimize (total-cost))", ")"]

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--planner-path", "-p", type=str)
    parser.add_argument("--separate-open-station", action="store_true")
    args = parser.parse_args()

    number_of_tasks, cycle_time, task_times, predecessors, _ = read_salbp1.read(
        args.input
    )
    domain = generate_domain(
        number_of_tasks, predecessors, separate_open_station=args.separate_open_station
    )
    name = os.path.basename(args.input)
    problem = generate_problem(name, number_of_tasks, cycle_time, task_times)

    with open("domain.pddl", "w") as f:
        f.write(domain)

    with open("problem.pddl", "w") as f:
        f.write(problem)

    if args.planner_path is not None:
        subprocess.run([args.planner_path, "domain.pddl", "problem.pddl", "plan.txt"])
