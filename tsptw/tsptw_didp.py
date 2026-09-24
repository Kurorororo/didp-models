#!/usr/bin/env python3

import argparse
import copy
import time

import didppy as dp
import read_tsptw

start = time.perf_counter()


def create_model(n, nodes, edges, a, b, mst=False):
    model = dp.Model()

    customer = model.add_object_type(number=n)
    unvisited = model.add_set_var(object_type=customer, target=[i for i in range(1, n)])
    location = model.add_element_var(object_type=customer, target=0)
    time = model.add_int_resource_var(target=max(0, a[0]), less_is_better=True)

    distance_matrix = [
        [edges[i, j] if (i, j) in edges else 0 for j in nodes] for i in nodes
    ]
    distance = model.add_int_table(distance_matrix)

    shortest_distance_matrix = copy.deepcopy(distance_matrix)

    for k in range(1, n):
        for i in range(n):
            for j in range(n):
                d = shortest_distance_matrix[i][k] + shortest_distance_matrix[k][j]

                if shortest_distance_matrix[i][j] > d:
                    shortest_distance_matrix[i][j] = d

    shortest_distance = model.add_int_table(shortest_distance_matrix)

    for i in range(1, n):
        model.add_state_constr(
            ~(unvisited.contains(i)) | (time + shortest_distance[location, i] <= b[i])
        )

    model.add_base_case(
        [unvisited.is_empty(), time + distance[location, 0] <= b[0]],
        cost=distance[location, 0],
    )

    state_cost = dp.IntExpr.state_cost()
    name_to_customer = {}

    for i in range(1, n):
        name = f"visit {i}"
        name_to_customer[name] = i
        visit = dp.Transition(
            name=name,
            cost=distance[location, i] + state_cost,
            effects=[
                (unvisited, unvisited.remove(i)),
                (location, i),
                (time, dp.max(time + distance[location, i], a[i])),
            ],
            preconditions=[unvisited.contains(i), time + distance[location, i] <= b[i]],
        )
        model.add_transition(visit)

    if mst:
        min_return = min(distance_matrix[i][0] for i in range(1, n)) if n > 1 else 0
        model.add_dual_bound(
            unvisited.is_empty().if_then_else(
                distance[location, 0],
                dp.minimum_spanning_tree(unvisited.add(location), distance)
                + min_return,
            )
        )
    else:
        min_to = model.add_int_table(
            [
                min((distance_matrix[i][j] for i in range(n) if i != j), default=0)
                for j in range(n)
            ]
        )
        min_from = model.add_int_table(
            [
                min((distance_matrix[i][j] for j in range(n) if i != j), default=0)
                for i in range(n)
            ]
        )
        model.add_dual_bound(min_to[unvisited] + min_to[0])
        model.add_dual_bound(min_from[unvisited] + min_from[location])

    return model, name_to_customer


def solve(
    model,
    name_to_customer,
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
        print("The problem is infeasible")

        return None, None
    else:
        tour = [0]

        for t in solution.transitions:
            tour.append(name_to_customer[t.name])

        tour.append(0)

        print(" ".join(map(str, tour[1:-1])))

        print(f"best bound: {solution.best_bound}")
        print(f"cost: {solution.cost}")

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
    parser.add_argument(
        "--mst",
        action="store_true",
        help="Use the MST dual bound instead of the default incoming/outgoing bounds",
    )
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--initial-beam-size", default=1, type=int)
    args = parser.parse_args()

    n, nodes, edges, a, b = read_tsptw.read(args.input)

    model, name_to_customer = create_model(n, nodes, edges, a, b, mst=args.mst)
    tour, cost = solve(
        model,
        name_to_customer,
        args.config,
        args.history,
        time_limit=args.time_out,
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
    )

    if cost is not None and read_tsptw.validate(n, edges, a, b, tour, cost):
        print("The solution is valid.")
    else:
        print("The solution is invalid.")
