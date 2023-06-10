#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp

import read_talent_scheduling


start = time.perf_counter()


def solve_minizinc_model(
    actor_to_scenes,
    actor_to_cost,
    scene_to_duration,
    all_different=False,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    n = len(scene_to_duration)
    m = len(actor_to_scenes)
    scenes = list(range(n))
    time_indices = list(range(n))
    actors = list(range(m))

    model = cp.CpoModel()
    x = cp.integer_var_list(n, min=0, max=n - 1)
    scene_done = [cp.integer_var_list(n, min=0, max=1) for _ in scenes]
    open_before = [cp.integer_var_list(n, min=0, max=1) for _ in actors]
    closed_before = [cp.integer_var_list(n, min=0, max=1) for _ in actors]

    if all_different:
        model.add_constraint(cp.all_diff(x))

    for s in scenes:
        model.add_constraint(scene_done[s][0] == 0)

    for t in time_indices[1:]:
        for s in scenes:
            pass
            model.add_constraint(
                scene_done[s][t] == scene_done[s][t - 1] + (x[t - 1] == s)
            )
            model.add_constraint(cp.if_then(scene_done[s][t] == 1, x[t] != s))

    for t in time_indices:
        for a in actors:
            open_rhs = False
            closed_rhs = 1

            if t > 0:
                open_rhs = open_before[a][t - 1] == 1

            for s in scenes:
                if actor_to_scenes[a][s] == 1:
                    open_rhs |= x[t] == s
                    closed_rhs *= scene_done[s][t]

            model.add_constraint(open_before[a][t] == open_rhs)
            model.add_constraint(closed_before[a][t] == closed_rhs)

    total = 0

    for t in time_indices:
        for a in actors:
            total += (
                cp.element(scene_to_duration, x[t])
                * actor_to_cost[a]
                * open_before[a][t]
                * (1 - closed_before[a][t])
            )

    model.add(cp.minimize(total))

    if history is None:
        if verbose:
            result = model.solve(TimeLimit=time_limit, Workers=threads)
        else:
            result = model.solve(
                TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
            )
    else:
        if verbose:
            solver = cp.CpoSolver(model, TimeLimit=time_limit, Workers=threads)
        else:
            solver = cp.CpoSolver(
                model, TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
            )
        with open(history, "w") as f:
            is_new_solution = True

            while is_new_solution:
                result = solver.search_next()
                is_new_solution = result.is_new_solution()

                if is_new_solution:
                    f.write(
                        "{}, {}\n".format(
                            time.perf_counter() - start,
                            result.get_objective_value(),
                        )
                    )

    is_optimal = result.is_solution_optimal()
    gap = result.get_objective_gap()
    best_bound = result.get_objective_bound()

    if result.is_solution():
        solution = [result[x[t]] for t in time_indices]
        cost = round(result.get_objective_value())
    else:
        solution = None
        cost = None

    is_infeasible = result.get_solve_status() == "infeasible"

    return solution, cost, is_optimal, gap, best_bound, is_infeasible


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--history", type=str)
    parser.add_argument("--all-different", action="store_true")
    args = parser.parse_args()

    _, actor_to_scenes, actor_to_cost, scene_to_duration = read_talent_scheduling.read(
        args.input
    )
    (
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
        single_actor_cost,
        scene_to_original,
    ) = read_talent_scheduling.simplify(
        actor_to_scenes, actor_to_cost, scene_to_duration
    )

    solution, cost, is_optimal, gap, best_bound, is_infeasible = solve_minizinc_model(
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
        all_different=args.all_different,
        time_limit=args.time_out,
        threads=args.threads,
        verbose=args.verbose,
        history=args.history,
    )

    if solution is not None:
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
            if is_optimal:
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(gap))
                print("best bound: {}".format(best_bound))
        else:
            print("The solution is invalid.")
    elif is_infeasible:
        print("The problem is infeasible.")
