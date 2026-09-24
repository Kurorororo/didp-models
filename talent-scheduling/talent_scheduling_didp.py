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
    actor = model.add_object_type(number=max(m, 1))
    remaining = model.add_set_var(object_type=scene, target=scene_list)

    actor_cost = model.add_int_table(actor_to_cost or [0])
    base_cost = model.add_int_table(base_cost)
    players = model.add_set_table(players, object_type=actor)

    model.add_base_case([remaining.is_empty()])

    came = model.add_set_state_fun(players.union(remaining.complement()), name="came")
    standby = model.add_set_state_fun(players.union(remaining) & came, name="standby")
    name_to_scene = {}
    state_cost = dp.IntExpr.state_cost()

    for s in scene_list:
        name = f"actor-equivalent-shoot {s}"
        name_to_scene[name] = s
        actor_equivalent_shoot = dp.Transition(
            name=name,
            cost=state_cost + base_cost[s],
            effects=[(remaining, remaining.remove(s))],
            preconditions=[remaining.contains(s), players[s] == standby],
        )
        model.add_transition(actor_equivalent_shoot, forced=True)

    transition_ids = []
    for s in scene_list:
        name = f"shoot {s}"
        name_to_scene[name] = s
        on_location = players[s] | standby

        shoot = dp.Transition(
            name=name,
            cost=state_cost + scene_to_duration[s] * actor_cost[on_location],
            effects=[(remaining, remaining.remove(s))],
            preconditions=[remaining.contains(s)],
        )
        transition_ids.append(model.add_transition(shoot))

    for s in scene_list:
        for t in subsumption_candidates[s]:
            model.add_transition_dominance(
                transition_ids[t],
                transition_ids[s],
                conditions=[players[t].issubset(came | players[s])],
            )
    model.add_dual_bound(base_cost[remaining])

    return model, name_to_scene


def solve(
    model,
    name_to_scene,
    solver_name,
    history,
    time_limit=None,
    seed=2023,
    initial_beam_size=1,
    threads=1,
):
    options = dict(time_limit=time_limit, quiet=False)
    if solver_name == "CAASDy":
        solver = dp.CAASDy(model, **options)
    elif solver_name == "CABS":
        solver = dp.CABS(
            model, initial_beam_size=initial_beam_size, threads=threads, **options
        )
    elif solver_name == "LNBS":
        solver = dp.LNBS(
            model,
            initial_beam_size=initial_beam_size,
            threads=threads,
            seed=seed,
            **options,
        )
    else:
        raise ValueError(f"Unknown solver: {solver_name}")

    with open(history, "w") as f:
        is_terminated = False

        while not is_terminated:
            solution, is_terminated = solver.search_next()

            if solution.cost is not None:
                f.write(f"{time.perf_counter() - start}, {solution.cost}\n")
                f.flush()

    print(f"Search time: {solution.time}s")
    print(f"Expanded: {solution.expanded}")
    print(f"Generated: {solution.generated}")

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
    parser.add_argument("--config", choices=["CAASDy", "CABS", "LNBS"], default="CABS")
    parser.add_argument("--seed", default=2023, type=int)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--initial-beam-size", default=1, type=int)
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
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
    )

    if is_infeasible:
        print("The problem is infeasible")
    else:
        print(f"best bound: {bound}")

        if cost is not None:
            print(f"cost: {cost}")

            if is_optimal:
                print(f"optimal cost: {cost}")

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
