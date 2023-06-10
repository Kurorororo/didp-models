#!/usr/bin/env python3

import argparse
import copy
import time

import didppy as dp
import read_tsptw

start = time.perf_counter()


def create_model(n, nodes, edges, a, b, non_zero_base_case):
    model = dp.Model()

    customer = model.add_object_type(number=n)
    unvisited = model.add_set_var(object_type=customer, target=[i for i in range(1, n)])
    location = model.add_element_var(object_type=customer, target=0)
    time = model.add_int_resource_var(target=0, less_is_better=True)

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

    if non_zero_base_case:
        model.add_base_case([unvisited.is_empty()], cost=distance[location, 0])
    else:
        model.add_base_case([location == 0, unvisited.is_empty()])

    state_cost = dp.IntExpr.state_cost()
    name_to_customer = {}

    for i in range(1, n):
        name = "visit {}".format(i)
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

    if not non_zero_base_case:
        name = "return"
        name_to_customer[name] = 0
        return_to_depot = dp.Transition(
            name=name,
            cost=distance[location, 0] + state_cost,
            effects=[(location, 0), (time, time + distance[location, 0])],
            preconditions=[unvisited.is_empty(), location != 0],
        )
        model.add_transition(return_to_depot)

    min_distance_to = model.add_int_table(
        [min(distance_matrix[i][j] for i in nodes if i != j) for j in nodes]
    )

    if non_zero_base_case:
        model.add_dual_bound(min_distance_to[unvisited] + min_distance_to[0])
    else:
        model.add_dual_bound(
            min_distance_to[unvisited]
            + (location != 0).if_then_else(min_distance_to[0], 0)
        )

    min_distance_from = model.add_int_table(
        [min(distance_matrix[i][j] for j in nodes if i != j) for i in nodes]
    )

    if non_zero_base_case:
        model.add_dual_bound(min_distance_from[unvisited] + min_distance_from[location])
    else:
        model.add_dual_bound(
            min_distance_from[unvisited]
            + (location != 0).if_then_else(min_distance_from[location], 0)
        )

    return model, name_to_customer


def solve(
    model,
    name_to_customer,
    solver_name,
    history,
    time_limit=None,
    non_zero_base_case=False,
):
    if solver_name == "FR":
        solver = dp.ForwardRecursion(model, time_limit=time_limit, quiet=False)
    elif solver_name == "BrFS":
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

    if solver_name == "FR":
        solution = solver.search()
    else:
        with open(history, "w") as f:
            is_terminated = False

            while not is_terminated:
                solution, is_terminated = solver.search_next()

                if solution.cost is not None:
                    f.write(
                        "{}, {}\n".format(time.perf_counter() - start, solution.cost)
                    )
                    f.flush()

    print("Search time: {}s".format(solution.time))

    if solution.is_infeasible:
        print("The problem is infeasible")

        return None, None
    else:
        tour = [0]

        for t in solution.transitions:
            tour.append(name_to_customer[t.name])

        if non_zero_base_case:
            tour.append(0)

        print(" ".join(map(str, tour[1:-1])))

        print("Search time: {}s".format(solution.time))
        print("Expanded: {}".format(solution.expanded))
        print("Generated: {}".format(solution.generated))
        print("cost: {}".format(solution.cost))
        print("best bound: {}".format(solution.best_bound))

        if solution.is_optimal:
            print("optimal cost: {}".format(solution.cost))

        return tour, solution.cost


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-out", default=1800, type=int)
    parser.add_argument("--history", default="history.csv", type=str)
    parser.add_argument("--config", default="CABS", type=str)
    parser.add_argument("--non-zero-base-case", action="store_true")
    args = parser.parse_args()

    n, nodes, edges, a, b = read_tsptw.read(args.input)

    model, name_to_customer = create_model(
        n, nodes, edges, a, b, args.non_zero_base_case
    )
    tour, cost = solve(
        model,
        name_to_customer,
        args.config,
        args.history,
        time_limit=args.time_out,
        non_zero_base_case=args.non_zero_base_case,
    )

    if cost is not None and read_tsptw.validate(n, edges, a, b, tour, cost):
        print("The solution is valid.")
    else:
        print("The solution is invalid.")
