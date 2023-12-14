#! /usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_salbp1
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


def generate_problem(
    number_of_tasks, cycle_time, task_times, predecessors, blind=False
):
    lines = [
        "object_numbers:",
        "      task: {}".format(number_of_tasks),
        "target:",
        "      uncompleted: [ "
        + ", ".join([str(i) for i in range(number_of_tasks)])
        + " ]",
        "      idle-time: 0",
        "table_values:",
        "      cycle-time: {}".format(cycle_time),
        "      time: { "
        + ", ".join(
            ["{}: {}".format(i, task_times[i + 1]) for i in range(number_of_tasks)]
        )
        + " }",
        "      predecessors: {",
    ]
    for i in range(number_of_tasks):
        lines += [
            "            {}: [ ".format(i)
            + ", ".join([str(j - 1) for j in predecessors[i + 1]])
            + " ],"
        ]
    lines += ["      }"]

    if not blind:
        lines += [
            "      lb2-weight1: { "
            + ", ".join(
                [
                    "{}: {}".format(i, 1)
                    for i in range(number_of_tasks)
                    if task_times[i + 1] > cycle_time / 2
                ]
            )
            + " }",
            "      lb2-weight2: { "
            + ", ".join(
                [
                    "{}: {}".format(i, 0.5)
                    for i in range(number_of_tasks)
                    if task_times[i + 1] == cycle_time / 2
                ]
            )
            + " }",
            "      lb3-weight: { "
            + ", ".join(
                [
                    "{}: {}".format(i, 1.0)
                    if task_times[i + 1] > cycle_time * 2 / 3
                    else "{}: {}".format(i, 2 / 3 // 0.001 / 1000)
                    if task_times[i + 1] == cycle_time * 2 / 3
                    else "{}: {}".format(i, 0.5)
                    if task_times[i + 1] > cycle_time / 3
                    else "{}: {}".format(i, 1 / 3 // 0.001 / 1000)
                    for i in range(number_of_tasks)
                    if task_times[i + 1] >= cycle_time / 3
                ]
            )
            + " }",
        ]

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()

    number_of_tasks, cycle_time, task_times, predecessors, _ = read_salbp1.read(
        args.input
    )
    problem = generate_problem(number_of_tasks, cycle_time, task_times, predecessors)

    with open("problem.yaml", "w") as f:
        f.write(problem)

    if args.blind:
        domain_path = os.path.join(os.path.dirname(__file__), "domain_blind.yaml")
    else:
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
            if transition["name"] == "open-new-station":
                solution.append([])
            else:
                solution[-1].append(transition["parameters"]["t"] + 1)

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_salbp1.validate(
            number_of_tasks, cycle_time, task_times, predecessors, solution, cost
        )
        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
