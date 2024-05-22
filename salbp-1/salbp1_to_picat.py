#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_salbp1

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


def write_picat_input(number_of_tasks, cycle_time, task_times, followers, filepath):
    with open(filepath, "w") as f:
        f.write("{}\n".format(number_of_tasks))
        f.write("{}\n".format(cycle_time))
        f.write(
            " ".join(str(task_times[i]) for i in range(1, number_of_tasks + 1)) + "\n"
        )
        n_relations = sum(len(followers[i]) for i in range(1, number_of_tasks + 1))
        f.write("{}\n".format(n_relations))

        for i in range(1, number_of_tasks + 1):
            for j in followers[i]:
                f.write("{} {}\n".format(i, j))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--picat-path", "-p", type=str)
    args = parser.parse_args()

    number_of_tasks, cycle_time, task_times, _, followers = read_salbp1.read(args.input)
    write_picat_input(number_of_tasks, cycle_time, task_times, followers, "problem.txt")

    if args.picat_path:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        dirname = os.path.dirname(__file__)
        subprocess.run(
            [args.picat_path, os.path.join(dirname, "salbp1_bb.pi"), "problem.txt"],
            preexec_fn=fn,
        )

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
