#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_single_machine_scheduling

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


def generate_picat_input(processing_times, due_dates, weights, before):
    lines = (
        [
            str(len(processing_times)),
        ]
        + [
            "{} {} {}".format(p, d, w)
            for (p, d, w) in zip(processing_times, due_dates, weights)
        ]
        + [str(sum(len(b) for b in before))]
    )

    for i, b in enumerate(before):
        for j in b:
            lines.append("{} {}".format(j + 1, i + 1))

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--picat-path", "-p", type=str)
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

    problem = generate_picat_input(processing_times, due_dates, weights, before)

    with open("problem.txt", "w") as f:
        f.write(problem)

    if args.picat_path is not None:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        print("Preprocessing time: {}s".format(time.perf_counter() - start))
        dirname = os.path.dirname(__file__)
        subprocess.run(
            [args.picat_path, os.path.join(dirname, "wt_bb"), "problem.txt"],
            preexec_fn=fn,
        )

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
