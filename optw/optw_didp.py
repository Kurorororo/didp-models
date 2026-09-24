#!/usr/bin/env python3

import argparse
import math
import time

import didppy as dp
import read_optw

start = time.perf_counter()


def compute_shortest_distance(distance, service_time):
    vertices = list(range(len(distance)))
    shortest_distance = [
        [distance[i][j] + service_time[i] for j in vertices] for i in vertices
    ]

    for k in vertices:
        if k == 0:
            continue

        for i in vertices:
            if k == i:
                continue
            for j in vertices:
                if k == j or i == j:
                    continue

                d = shortest_distance[i][k] + shortest_distance[k][j]

                if shortest_distance[i][j] > d:
                    shortest_distance[i][j] = d

    return shortest_distance


def create_model(
    vertices,
    service_time,
    profit,
    opening,
    closing,
    distance,
    epsilon=1e-6,
    blind=False,
):
    """Maximize collected profit with reachability filtering and knapsack bounds.

    Time denotes the start of service. Shortest times include service at the
    origin, keeping filters sound even for rounded, nonmetric travel times.
    """
    if not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("epsilon must be finite and nonnegative")
    model = dp.Model(maximize=True)
    goal = len(vertices)
    node = model.add_object_type(number=goal + 1)
    travel = [[service_time[i] + distance[i][j] for j in vertices] for i in vertices]
    shortest = compute_shortest_distance(distance, service_time)
    initial_time = max(0, opening[0])
    initially_reachable = [
        i
        for i in vertices[1:]
        if max(initial_time + shortest[0][i], opening[i])
        <= min(closing[i], closing[0] - shortest[i][0])
    ]
    reachable = model.add_set_resource_var(
        object_type=node,
        target=initially_reachable,
        less_is_better=False,
        name="reachable",
    )
    location = model.add_element_var(object_type=node, target=0, name="location")
    current_time = model.add_int_resource_var(
        target=initial_time, less_is_better=True, name="time"
    )
    travel_table = model.add_int_table(travel + [[0] * goal])
    shortest_table = model.add_int_table(shortest + [[0] * goal])
    opening_table = model.add_int_table(opening)
    closing_table = model.add_int_table(closing)
    return_table = model.add_int_table([shortest[i][0] for i in vertices])
    model.add_state_constr(current_time <= closing[0])
    model.add_base_case([location == goal])
    k = model.add_local_var()
    names = {}
    for i in vertices[1:]:
        name = f"visit {i}"
        names[name] = i
        time_next = model.add_int_state_fun(
            dp.max(current_time + travel_table[location, i], opening[i])
        )
        earliest = dp.max(time_next + shortest_table[i, k], opening_table[k])
        model.add_transition(
            dp.Transition(
                name=name,
                cost=profit[i] + dp.IntExpr.state_cost(),
                effects=[
                    (location, i),
                    (current_time, time_next),
                    (
                        reachable,
                        reachable.remove(i).filter(
                            k,
                            (earliest <= closing_table[k])
                            & (earliest + return_table[k] <= closing[0]),
                        ),
                    ),
                ],
                preconditions=[
                    location != goal,
                    reachable.contains(i),
                    time_next <= closing[i],
                    time_next + shortest[i][0] <= closing[0],
                ],
            )
        )
    # Stopping is optional in OPTW. Returning collects no profit, so this
    # transition naturally has zero objective cost (unlike distance objectives).
    model.add_transition(
        dp.Transition(
            name="finish",
            cost=dp.IntExpr.state_cost(),
            effects=[
                (location, goal),
                (current_time, current_time + travel_table[location, 0]),
                (reachable, model.create_set_const(object_type=node, value=[])),
            ],
            preconditions=[
                location != goal,
                current_time + travel_table[location, 0] <= closing[0],
            ],
        )
    )
    if not blind:
        rewards = model.add_int_table([max(0, p) for p in profit])
        min_from = [
            min((travel[i][j] for j in vertices if j != i), default=0) for i in vertices
        ]
        min_to = [
            min((travel[i][j] for i in vertices if i != j), default=0) for j in vertices
        ]
        from_table = model.add_int_table(min_from + [0])
        for weights, capacity in [
            (min_from, closing[0] - current_time - from_table[location]),
            (min_to, closing[0] - current_time - min_to[0]),
        ]:
            weights_table = model.add_int_table(weights)
            bound = dp.fractional_knapsack(
                reachable, dp.max(capacity, 0), rewards, weights_table
            )
            model.add_dual_bound(
                (location == goal).if_then_else(0, math.floor(bound + epsilon))
            )
    return model, names


def create_solver(
    model,
    solver_name,
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

    return solver


def solve(
    model,
    name_to_node,
    solver_name,
    history,
    time_limit=None,
    seed=2023,
    initial_beam_size=1,
    threads=1,
):
    solver = create_solver(
        model,
        solver_name,
        time_limit=time_limit,
        seed=seed,
        initial_beam_size=initial_beam_size,
        threads=threads,
    )

    with open(history, "w") as f:
        is_terminated = False

        while not is_terminated:
            solution, is_terminated = solver.search_next()

            if solution.cost is not None:
                f.write(f"{time.perf_counter() - start}, {solution.cost}\n")
                f.flush()

    print(f"Search time: {solution.time}s")

    if solution.cost is None:
        if solution.is_infeasible:
            print("The problem is infeasible")
        else:
            print("No solution found within the time limit")

        return None, None
    else:
        tour = [0]

        for t in solution.transitions:
            if t.name in name_to_node:
                tour.append(name_to_node[t.name])

        tour.append(0)

        print(" ".join(map(str, tour[1:-1])))

        print(f"Expanded: {solution.expanded}")
        print(f"Generated: {solution.generated}")
        print(f"cost: {solution.cost}")
        print(f"best bound: {solution.best_bound}")

        if solution.is_optimal:
            print(f"optimal cost: {solution.cost}")

        return tour, solution.cost


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-out", default=1800, type=int)
    parser.add_argument("--history", default="history.csv", type=str)
    parser.add_argument("--config", choices=["CAASDy", "CABS", "LNBS"], default="CABS")
    parser.add_argument("--seed", default=2023, type=int)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--initial-beam-size", default=1, type=int)
    parser.add_argument("--round-to-second", action="store_true")
    parser.add_argument("--epsilon", type=float, default=1e-6)
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()

    vertices, service_time, profit, opening, closing, distance = read_optw.read_optw(
        args.input
    )

    if args.round_to_second:
        service_time, opening, closing, distance = read_optw.round_to_second(
            service_time, opening, closing, distance
        )
    else:
        service_time, opening, closing, distance = read_optw.round_to_first(
            service_time, opening, closing, distance
        )

    model, name_to_node = create_model(
        vertices,
        service_time,
        profit,
        opening,
        closing,
        distance,
        epsilon=args.epsilon,
        blind=args.blind,
    )

    tour, cost = solve(
        model,
        name_to_node,
        args.config,
        args.history,
        time_limit=args.time_out,
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
    )

    if cost is not None and read_optw.validate_optw(
        service_time, profit, opening, closing, distance, tour, cost
    ):
        print("The solution is valid.")
    elif cost is not None:
        print("The solution is invalid.")
