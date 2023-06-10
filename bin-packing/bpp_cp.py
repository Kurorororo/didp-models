#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp

import read_bpp


start = time.perf_counter()


def solve(n, c, weights, time_limit=None, threads=1, history=None):
    model = cp.CpoModel()
    ub, weights = read_bpp.first_fit_decreasing(c, weights)
    where = [cp.integer_var(0, min(i, ub - 1)) for i in range(n)]
    load = cp.integer_var_list(ub, 0, c)
    model.add(cp.pack(load, where, weights))
    model.add(cp.minimize(cp.max(where) + 1))

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
        cost = round(result.get_objective_value())
        bin_to_items = {}
        for i in range(n):
            bin = result[where[i]]

            if bin not in bin_to_items:
                bin_to_items[bin] = []

            bin_to_items[bin].append(i)

        solution = [bin_to_items[bin] for bin in range(cost)]
        print(solution)
        print("cost: {}".format(cost))
        validation_result = read_bpp.validate(n, c, weights, solution, cost)
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
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    n, c, weights = read_bpp.read(args.input)
    solve(
        n,
        c,
        weights,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
    )
