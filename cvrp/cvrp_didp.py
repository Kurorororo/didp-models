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

    model.add_base_case([unvisited.is_empty(), location == 0])
    name_to_partial_tour = {}

    for i in range(1, n):
        name = "visit {}".format(i)
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
        name = "visit {} via depot".format(i)
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
            preconditions=[unvisited.contains(i), vehicles < k],
        )
        model.add_transition(visit_via_depot)

    name = "return"
    name_to_partial_tour[name] = (nodes[0],)
    return_to_depot = dp.Transition(
        name=name,
        cost=dp.IntExpr.state_cost() + distance[location, 0],
        effects=[(location, 0)],
        preconditions=[unvisited.is_empty(), location != 0],
    )
    model.add_transition(return_to_depot)

    model.add_state_constr((k - vehicles + 1) * capacity >= load + demand[unvisited])

    min_distance_to = model.add_int_table(
        [min(distance_matrix[i][j] for i in range(n) if i != j) for j in range(n)]
    )
    model.add_dual_bound(
        min_distance_to[unvisited] + (location != 0).if_then_else(min_distance_to[0], 0)
    )

    min_distance_from = model.add_int_table(
        [min(distance_matrix[i][j] for j in range(n) if i != j) for i in range(n)]
    )
    model.add_dual_bound(
        min_distance_from[unvisited]
        + (location != 0).if_then_else(min_distance_from[location], 0)
    )

    return model, name_to_partial_tour


def solve(
    model,
    name_to_partial_tour,
    solver_name,
    history,
    time_limit=None,
):
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
        tour = [1]

        for t in solution.transitions:
            tour += list(name_to_partial_tour[t.name])

        return tour, solution.cost, solution.best_bound, solution.is_optimal, False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-out", default=1800, type=int)
    parser.add_argument("--history", default="history.csv", type=str)
    parser.add_argument("--config", default="CABS", type=str)
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
    )

    if is_infeasible:
        print("The problem is infeasible.")
    else:
        print("best bound: {}".format(bound))

        if cost is not None:
            print(" ".join(map(str, solution)))
            print("cost: {}".format(cost))

            if is_optimal:
                print("optimal cost: {}".format(cost))

            validation_result = read_tsplib.validate_cvrp(
                n, nodes, edges, capacity, demand, depot, solution, cost, k
            )

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
