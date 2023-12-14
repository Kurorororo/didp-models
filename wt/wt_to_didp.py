#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_single_machine_scheduling
import yaml

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


def generate_problem(processing_times, due_dates, weights, before):
    n = len(processing_times)
    lines = [
        "object_numbers:",
        "    job: {}".format(n),
        "target:",
        "    scheduled: []",
        "table_values:",
        "    all_jobs: [ " + ", ".join(str(i) for i in range(n)) + " ]",
        "    processing_time: {"
        + ", ".join("{}: {}".format(i, processing_times[i]) for i in range(n))
        + " }",
        "    due_date: {"
        + ", ".join("{}: {}".format(i, due_dates[i]) for i in range(n))
        + " }",
        "    weight: {"
        + ", ".join("{}: {}".format(i, weights[i]) for i in range(n))
        + " }",
        "    predecessors: {",
    ]
    for i in range(n):
        lines.append(
            "                 {}: [ ".format(i)
            + ", ".join(str(j) for j in before[i])
            + " ],"
        )
    lines.append("    }")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--precedence", action="store_true")
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    args = parser.parse_args()

    if args.precedence:
        (
            processing_times,
            due_dates,
            weights,
            original_before,
            original_after,
        ) = read_single_machine_scheduling.read_wt_prec(args.input)
        before = original_before
        before, _ = read_single_machine_scheduling.extract_precedence_for_wt_prec(
            processing_times, due_dates, weights, original_before, original_after
        )
    else:
        (
            processing_times,
            due_dates,
            weights,
        ) = read_single_machine_scheduling.read_wt(args.input)
        original_before = None
        before, _ = read_single_machine_scheduling.extract_precedence_for_wt(
            processing_times, due_dates, weights
        )

    problem = generate_problem(processing_times, due_dates, weights, before)

    with open("problem.yaml", "w") as f:
        f.write(problem)

    domain_path = os.path.join(os.path.dirname(__file__), "domain.yaml")

    if args.didp_path is not None:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        print("Preprocessing time: {}s".format(time.perf_counter() - start))
        subprocess.run(
            [args.didp_path, domain_path, "problem.yaml", args.config_path],
            preexec_fn=fn,
        )

    if os.path.exists("solution.yaml"):
        with open("solution.yaml") as f:
            result = yaml.safe_load(f)
        cost = round(result["cost"])
        solution = []
        for transition in result["transitions"]:
            solution.append(transition["parameters"]["j"])

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_single_machine_scheduling.verify_wt(
            solution,
            processing_times,
            due_dates,
            weights,
            cost=cost,
            before=original_before,
        )

        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
