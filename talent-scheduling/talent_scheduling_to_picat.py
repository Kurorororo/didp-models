#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_talent_scheduling

start = time.perf_counter()


def get_subsumption_candidates(players):
    n = len(players)
    candidates = [[] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i != j:
                if set(players[i]) <= set(players[j]):
                    candidates[i].append(j)

    return candidates


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


def create_picat_input(actor_to_scenes, actor_to_cost, scene_to_duration):
    n = len(scene_to_duration)
    m = len(actor_to_scenes)

    lines = [str(n), str(m)]

    for a in range(m):
        line = []
        for s in range(n):
            line.append(str(actor_to_scenes[a][s]))
        line.append(str(actor_to_cost[a]))
        lines.append(" ".join(line))

    lines.append(" ".join([str(d) for d in scene_to_duration]))

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--picat-path", "-p", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    args = parser.parse_args()

    (
        name,
        actor_to_scenes,
        actor_to_cost,
        scene_to_duration,
    ) = read_talent_scheduling.read(args.input)
    (
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
        single_actor_cost,
        scene_to_original,
    ) = read_talent_scheduling.simplify(
        actor_to_scenes, actor_to_cost, scene_to_duration
    )

    problem = create_picat_input(
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
    )

    with open("problem.txt", "w") as f:
        f.write(problem)

    if args.picat_path is not None:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        print("Preprocessing time: {}s".format(time.perf_counter() - start))
        dirname = os.path.dirname(__file__)
        subprocess.run(
            [
                args.picat_path,
                os.path.join(dirname, "talent_scheduling_bb"),
                "problem.txt",
            ],
            preexec_fn=fn,
        )

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
