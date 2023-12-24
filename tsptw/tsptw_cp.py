#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp
import read_tsptw

start = time.perf_counter()


def solve(nodes, edges, a, b, time_limit=None, threads=1, history=None):
    edges_matrix = [
        [edges[i, j] if (i, j) in edges else 0 for j in nodes] for i in nodes
    ]

    model = cp.CpoModel()
    x = []
    for i in nodes:
        if i == 0:
            x.append(cp.interval_var(start=0, length=0))
        else:
            x.append(
                cp.interval_var(
                    start=(a[i], cp.INTERVAL_MAX), end=(a[i], b[i]), length=0
                )
            )

    pi = cp.sequence_var(x, types=nodes)
    distance = cp.transition_matrix(edges_matrix)
    model.add(cp.no_overlap(pi, distance, is_direct=True))
    model.add(cp.first(pi, x[0]))
    model.add(
        cp.minimize(
            cp.sum(
                [
                    cp.element(edges_matrix[i], cp.type_of_next(pi, x[i], 0))
                    for i in nodes
                ]
            )
        )
    )

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
        scheduled = set([0])
        solution = [0]
        while len(scheduled) < len(nodes):
            min_s = -1
            argmin = -1
            for i in nodes[1:]:
                if i not in scheduled:
                    s = result[x[i]].start
                    if min_s == -1 or s < min_s:
                        min_s = s
                        argmin = i
            if argmin != -1:
                scheduled.add(argmin)
                solution.append(argmin)
        solution.append(0)
        cost = result.get_objective_value()
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_tsptw.validate(len(nodes), edges, a, b, solution, cost)

        if validation_result:
            print("The solution is valid.")
            if result.is_solution_optimal():
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(result.get_objective_gap()))
                print("best bound: {}".format(result.get_objective_bound()))
        else:
            print("The solution is invalid")
    elif result.get_solve_status() == "Infeasible":
        print("The problem is infeasible.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    _, nodes, edges, a, b = read_tsptw.read(args.input)
    solve(
        nodes,
        edges,
        a,
        b,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
    )
