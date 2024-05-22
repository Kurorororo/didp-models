#!/usr/bin/env python3

import argparse
import os
import re
import time

import docplex.cp.model as cp
import read_tsplib

start = time.perf_counter()


def solve_alternative(
    n,
    nodes,
    edges,
    capacity,
    demand,
    depot,
    routes=None,
    manually_alternative=False,
    time_limit=None,
    threads=1,
    history=None,
):
    m = n if routes is None else routes
    node_to_idx = {j: i for i, j in enumerate(nodes)}
    edges_matrix = [
        [edges[i, j] if (i, j) in edges else 0 for j in nodes] for i in nodes
    ]

    model = cp.CpoModel()
    tvisit = [
        [
            (
                cp.interval_var(start=0, length=1)
                if i == depot
                else cp.interval_var(length=1, optional=True)
            )
            for i in nodes
        ]
        for _ in range(m)
    ]

    if not manually_alternative:
        visit = [
            (
                cp.interval_var(start=0, length=1)
                if i == depot
                else cp.interval_var(length=1)
            )
            for i in nodes
        ]

    pi = [cp.sequence_var(tvisit[k], list(range(n))) for k in range(m)]
    distance = cp.transition_matrix(edges_matrix)

    for k in range(m):
        model.add(cp.no_overlap(pi[k], distance))
        model.add(cp.first(pi[k], tvisit[k][node_to_idx[depot]]))
        model.add(
            cp.sum(
                cp.presence_of(tvisit[k][node_to_idx[i]]) * demand[i]
                for i in nodes
                if i != depot
            )
            <= capacity
        )

    for i in nodes:
        if i != depot:
            if manually_alternative:
                model.add(
                    cp.sum(cp.presence_of(tvisit[k][node_to_idx[i]]) for k in range(m))
                    == 1
                )
            else:
                model.add(
                    cp.alternative(
                        visit[node_to_idx[i]],
                        [tvisit[k][node_to_idx[i]] for k in range(m)],
                    )
                )

    model.add(
        cp.minimize(
            cp.sum(
                cp.element(
                    edges_matrix[node_to_idx[i]],
                    cp.type_of_next(
                        pi[k],
                        tvisit[k][node_to_idx[i]],
                        node_to_idx[depot],
                        node_to_idx[i],
                    ),
                )
                for k in range(m)
                for i in nodes
            )
        )
    )

    if not manually_alternative:
        phase = cp.search_phase(vars=pi)
        model.set_search_phases(phase)

    if args.history is None:
        result = model.solve(
            TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
        )
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
                            time.perf_counter() - start, result.get_objective_value()
                        )
                    )

    print("Search time: {}s".format(result.get_solve_time()))

    if result.is_solution():
        solution = []
        for k in range(m):
            time_with_nodes = []
            for i in nodes:
                v = result[tvisit[k][node_to_idx[i]]]
                if len(v) > 0:
                    time_with_nodes.append((v.start, i))
            if len(time_with_nodes) > 1:
                for _, i in sorted(time_with_nodes):
                    solution.append(i)
        solution.append(depot)

        cost = round(result.get_objective_value())
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_tsplib.validate_cvrp(
            n, nodes, edges, capacity, demand, depot, solution, cost, k=routes
        )

        if validation_result:
            print("The solution is valid.")
            if result.is_solution_optimal():
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(result.get_objective_gap()))
                print("best bound: {}".format(result.get_objective_bound()))
        else:
            print("The solution is invalid.")
    elif result.get_solve_status() == "infeasible":
        print("The problem is infeasible.")


def solve_single_resource(
    n,
    nodes,
    edges,
    capacity,
    demand,
    depot,
    routes=None,
    time_limit=None,
    threads=1,
    history=None,
):
    m = n if routes is None else routes
    model = cp.CpoModel()
    node_to_idx = {j: i for i, j in enumerate(nodes)}
    edges_matrix = [
        [edges[i, j] if (i, j) in edges else 0 for j in nodes] for i in nodes
    ]
    horizon = (
        max(edges[depot, j] for j in nodes if j != depot)
        + (n - 1)
        * max(
            edges[i, j]
            for i in nodes
            for j in nodes
            if i != depot and j != depot and (i, j) in edges
        )
        + max(edges[i, depot] for i in nodes if i != depot)
    )
    visit = [
        (
            cp.interval_var(start=0, end=0, length=0)
            if i == depot
            else cp.interval_var(
                start=(0, cp.INTERVAL_MAX), end=(0, m * horizon), length=0
            )
        )
        for i in nodes
    ]
    for i in range(m):
        visit.append(cp.interval_var(start=(i + 1) * horizon, length=0))
    space = cp.step_at_start(visit[node_to_idx[depot]], capacity)
    for i in nodes:
        if i != depot:
            space -= cp.step_at_start(visit[node_to_idx[i]], demand[i])
    for i in range(n, n + m):
        space += cp.step_at_start(visit[i], (0, capacity))
    model.add(cp.always_in(space, (0, m * horizon), 0, capacity))

    pi = cp.sequence_var(visit, list(range(n)) + [node_to_idx[depot]] * m)
    distance = cp.transition_matrix(edges_matrix)
    model.add(cp.no_overlap(pi, distance))
    model.add(cp.first(pi, visit[node_to_idx[depot]]))
    model.add(
        cp.minimize(
            cp.sum(
                cp.element(
                    edges_matrix[node_to_idx[i]],
                    cp.type_of_next(pi, visit[node_to_idx[i]], node_to_idx[depot]),
                )
                for i in nodes
            )
            + cp.sum(
                cp.element(
                    edges_matrix[node_to_idx[depot]],
                    cp.type_of_next(pi, visit[i], node_to_idx[depot]),
                )
                for i in range(n, n + m)
            )
        )
    )

    phase = cp.search_phase(vars=[pi])
    model.set_search_phases(phase)

    if args.history is None:
        result = model.solve(
            TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
        )
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
                            time.perf_counter() - start, result.get_objective_value()
                        )
                    )

    if result.is_solution():
        vehicle_to_route = [[] for _ in range(m)]
        for i in nodes:
            if i != depot:
                start_visit = result[visit[node_to_idx[i]]].start
                vehicle = start_visit // horizon
                vehicle_to_route[vehicle].append((start_visit, i))

        solution = []
        for k in range(m):
            if len(vehicle_to_route[k]) > 0:
                solution.append(depot)
                for _, i in sorted(vehicle_to_route[k]):
                    solution.append(i)
        solution.append(depot)
        cost = round(result.get_objective_value())
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_tsplib.validate_cvrp(
            n, nodes, edges, capacity, demand, depot, solution, cost, k=routes
        )

        if validation_result:
            print("The solution is valid.")
            if result.is_solution_optimal():
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(result.get_objective_gap()))
                print("best bound: {}".format(result.get_objective_bound()))
        else:
            print("The solution is invalid.")
    elif result.get_solve_status() == "infeasible":
        print("The problem is infeasible.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", "-t", type=int, default=1)
    parser.add_argument("--single-resource", "-s", action="store_true")
    parser.add_argument("--not-fix-route", "-n", action="store_true")
    parser.add_argument("--manually-alternative", action="store_true")
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    if args.not_fix_route:
        k = None
    else:
        name = os.path.basename(args.input)
        m = re.match(r".+k(\d+).+", name)
        k = int(m.group(1))

    n, nodes, edges, capacity, demand, depot, symmetric = read_tsplib.read_cvrp(
        args.input
    )
    if args.single_resource:
        solve_single_resource(
            n,
            nodes,
            edges,
            capacity,
            demand,
            depot,
            routes=k,
            time_limit=args.time_out,
            threads=args.threads,
            history=args.history,
        )
    else:
        solve_alternative(
            n,
            nodes,
            edges,
            capacity,
            demand,
            depot,
            routes=k,
            manually_alternative=args.manually_alternative,
            time_limit=args.time_out,
            threads=args.threads,
            history=args.history,
        )
