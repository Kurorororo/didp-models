#!/usr/bin/env python3

import argparse
import time

import didppy as dp
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


def create_model(actor_to_scenes, actor_to_cost, scene_to_duration, base_cost):
    n = len(scene_to_duration)
    m = len(actor_to_scenes)
    scene_list = list(range(n))
    actor_list = list(range(m))
    players = [
        [j for j in actor_list if actor_to_scenes[j][i] == 1] for i in scene_list
    ]
    subsumption_candidates = get_subsumption_candidates(players)

    model = dp.Model()

    scene = model.add_object_type(number=n)
    actor = model.add_object_type(number=m)
    remaining = model.add_set_var(object_type=scene, target=scene_list)

    actor_cost = model.add_int_table(actor_to_cost)
    base_cost = model.add_int_table(base_cost)
    players = model.add_set_table(players, object_type=actor)

    model.add_base_case([remaining.is_empty()])

    name_to_scene = {}
    state_cost = dp.IntExpr.state_cost()

    for s in scene_list:
        name = "actor-equivalent-shoot {}".format(s)
        name_to_scene[name] = s
        standby = players.union(remaining) & players.union(remaining.complement())
        actor_equivalent_shoot = dp.Transition(
            name=name,
            cost=state_cost + base_cost[s],
            effects=[(remaining, remaining.remove(s))],
            preconditions=[remaining.contains(s), players[s] == standby],
        )
        model.add_transition(actor_equivalent_shoot, forced=True)

    for s in scene_list:
        name = "shoot {}".format(s)
        name_to_scene[name] = s
        standby = players.union(remaining) & players.union(remaining.complement())
        on_location = players[s] | standby

        preconditions = [
            ~remaining.contains(t)
            | ~players[t].issubset(players.union(remaining.complement()) | players[s])
            for t in scene_list
            if t in subsumption_candidates[s]
        ]
        shoot = dp.Transition(
            name=name,
            cost=state_cost + scene_to_duration[s] * actor_cost[on_location],
            effects=[(remaining, remaining.remove(s))],
            preconditions=[remaining.contains(s)] + preconditions,
        )
        model.add_transition(shoot)

    model.add_dual_bound(base_cost[remaining])

    return model, name_to_scene


def solve(model, name_to_scene, solver_name, history, time_limit=None):
    if solver_name == "BrFS":
        solver = dp.BreadthFirstSearch(model, time_limit=time_limit, quiet=False)
    elif solver_name == "CAASDy":
        solver = dp.CAASDy(model, time_limit=time_limit, quiet=False)
    elif solver_name == "DFBB":
        solver = dp.DFBB(model, time_limit=time_limit, quiet=False)
    elif solver_name == "CBFS":
        solver = dp.CBFS(model, time_limit=time_limit, quiet=False)
    elif solver_name == "ACPS":
        solver = dp.ACPS(model, time_limit=time_limit, quiet=False)
    elif solver_name == "APPS":
        solver = dp.APPS(model, time_limit=time_limit, quiet=False)
    elif solver_name == "DBDFS":
        solver = dp.DBDFS(model, time_limit=time_limit, quiet=False)
    else:
        solver = dp.CABS(model, time_limit=time_limit, quiet=False)

    with open(history, "w") as f:
        is_terminated = False

        while not is_terminated:
            solution, is_terminated = solver.search_next()

            if solution.cost is not None:
                f.write("{}, {}\n".format(time.perf_counter() - start, solution.cost))
                f.flush()

    print("Search time: {}s".format(solution.time))
    print("Expanded: {}".format(solution.expanded))
    print("Generated: {}".format(solution.generated))

    if solution.is_infeasible:
        return None, None, None, False, True
    else:
        permutation = [name_to_scene[t.name] for t in solution.transitions]

        return (
            permutation,
            solution.cost,
            solution.best_bound,
            solution.is_optimal,
            False,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-out", default=1800, type=int)
    parser.add_argument("--history", default="history.csv", type=str)
    parser.add_argument("--config", default="CABS", type=str)
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

    model, name_to_scene = create_model(
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
        base_cost,
    )
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_scene,
        args.config,
        args.history,
        time_limit=args.time_out,
    )

    if is_infeasible:
        print("The problem is infeasible")
    else:
        print("best bound: {}".format(bound))

        if cost is not None:
            print("cost: {}".format(cost))

            if is_optimal:
                print("optimal cost: {}".format(cost))

            if solution is not None:
                (
                    solution,
                    reconstructed_cost,
                ) = read_talent_scheduling.reconstruct_solution(
                    solution, cost, single_actor_cost, scene_to_original
                )

                print(solution)

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
