#!/usr/bin/env python3

import argparse
import os
import re
import time

import didppy as dp
import read_tsplib

start = time.perf_counter()


def create_model(n, nodes, edges, capacity, demand, k):
    model = dp.Model()
    customer = model.add_object_type(number=n)
    unvisited = model.add_set_var(object_type=customer, target=[i for i in range(1, n)])
    location = model.add_element_var(object_type=customer, target=0)
    load = model.add_int_resource_var(target=0, less_is_better=True)
    vehicles = model.add_int_resource_var(target=1, less_is_better=True)
    demand = model.add_int_table([demand[i] for i in nodes])
    distance_matrix = [
        [edges[i, j] if (i, j) in edges else 0 for j in nodes] for i in nodes
    ]
    distance = model.add_int_table(distance_matrix)
    distance_via_depot = model.add_int_table(
        [
            [
                edges[i, nodes[0]] + edges[nodes[0], j]
                if (i, nodes[0]) in edges and (nodes[0], j) in edges
                else edges[i, j]
                if (i, j) in edges
                else 0
                for j in nodes
            ]
            for i in nodes
        ]
    )

    model.add_base_case([unvisited.is_empty()], cost=distance[location, 0])
    name_to_partial_tour = {}

    for i in range(1, n):
        name = f"visit {i}"
        name_to_partial_tour[name] = (nodes[i],)
        visit = dp.Transition(
            name=name,
            cost=dp.IntExpr.state_cost() + distance[location, i],
            effects=[
                (unvisited, unvisited.remove(i)),
                (location, i),
                (load, load + demand[i]),
            ],
            preconditions=[unvisited.contains(i), load + demand[i] <= capacity],
        )
        model.add_transition(visit)

    for i in range(1, n):
        name = f"visit {i} via depot"
        name_to_partial_tour[name] = (nodes[0], nodes[i])
        visit_via_depot = dp.Transition(
            name=name,
            cost=dp.IntExpr.state_cost() + distance_via_depot[location, i],
            effects=[
                (unvisited, unvisited.remove(i)),
                (location, i),
                (load, demand[i]),
                (vehicles, vehicles + 1),
            ],
            preconditions=[unvisited.contains(i), vehicles < k, demand[i] <= capacity],
        )
        model.add_transition(visit_via_depot)

    model.add_state_constr((k - vehicles + 1) * capacity >= load + demand[unvisited])

    # A compressed edge can traverse the depot when opening a new route.
    # Taking the cheaper alternative keeps the MST valid even after rounding
    # breaks the triangle inequality.
    mst_distance = model.add_int_table(
        [
            [
                min(
                    distance_matrix[i][j], distance_matrix[i][0] + distance_matrix[0][j]
                )
                for j in range(n)
            ]
            for i in range(n)
        ]
    )
    min_return = min((distance_matrix[i][0] for i in range(1, n)), default=0)
    model.add_dual_bound(
        unvisited.is_empty().if_then_else(
            distance[location, 0],
            dp.minimum_spanning_tree(unvisited.add(location), mst_distance)
            + min_return,
        )
    )

    return model, name_to_partial_tour


def solve(
    model,
    name_to_partial_tour,
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
        tour = [1]

        for t in solution.transitions:
            tour += list(name_to_partial_tour[t.name])

        tour.append(tour[0])

        return tour, solution.cost, solution.best_bound, solution.is_optimal, False


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

    name = os.path.basename(args.input)
    m = re.match(r".+k(\d+).+", name)
    k = int(m.group(1))

    (
        n,
        nodes,
        edges,
        capacity,
        demand,
        depot,
        _,
    ) = read_tsplib.read_cvrp(args.input)
    model, name_to_partial_tour = create_model(n, nodes, edges, capacity, demand, k)
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_partial_tour,
        args.config,
        args.history,
        time_limit=args.time_out,
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
    )

    if is_infeasible:
        print("The problem is infeasible.")
    else:
        print(f"best bound: {bound}")

        if cost is not None:
            print(" ".join(map(str, solution)))
            print(f"cost: {cost}")

            if is_optimal:
                print(f"optimal cost: {cost}")

            validation_result = read_tsplib.validate_cvrp(
                n, nodes, edges, capacity, demand, depot, solution, cost, k
            )

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
