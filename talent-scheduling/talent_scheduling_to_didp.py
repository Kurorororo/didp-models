#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_talent_scheduling
import yaml

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


def generate_problem(
    name, actor_to_scenes, actor_to_cost, scene_to_duration, base_cost
):
    n = len(scene_to_duration)
    m = len(actor_to_scenes)
    players = [[j for j in range(m) if actor_to_scenes[j][i] == 1] for i in range(n)]
    subsumption_candidates = get_subsumption_candidates(players)
    lines = [
        "object_numbers:",
        "    scene: {}".format(n),
        "    actor: {}".format(m),
        "target:",
        "    remaining: [ " + ", ".join(str(i) for i in range(n)) + " ]",
        "table_values:",
        "    duration: { "
        + ", ".join("{}: {}".format(i, scene_to_duration[i]) for i in range(n))
        + " }",
        "    actor_cost: { "
        + ", ".join("{}: {}".format(i, actor_to_cost[i]) for i in range(m))
        + " }",
        "    base_cost: { "
        + ", ".join("{}: {}".format(i, base_cost[i]) for i in range(n))
        + " }",
        "    players: {",
    ]
    for i in range(n):
        lines += [
            "        {}: [ ".format(i) + ", ".join(str(j) for j in players[i]) + " ],",
        ]
    lines += ["      }"]
    lines += ["    subsumption_candidates: {"]
    for i in range(n):
        lines += [
            "        {}: [ ".format(i)
            + ", ".join(str(j) for j in subsumption_candidates[i])
            + " ],",
        ]
    lines += ["      }"]

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--blind", action="store_true")
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
    base_cost = read_talent_scheduling.compute_base_costs(
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
    )

    problem = generate_problem(
        name,
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
        base_cost,
    )

    with open("problem.yaml", "w") as f:
        f.write(problem)

    domain_file_name = "domain_blind.yaml" if args.blind else "domain.yaml"
    domain_path = os.path.join(os.path.dirname(__file__), domain_file_name)

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
            solution.append(transition["parameters"]["s"])

        solution, reconstructed_cost = read_talent_scheduling.reconstruct_solution(
            solution, cost, single_actor_cost, scene_to_original
        )

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_talent_scheduling.validate(
            solution,
            reconstructed_cost,
            actor_to_scenes,
            actor_to_cost,
            scene_to_duration,
        )

        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
