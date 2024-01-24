#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp
import read_mdkp

start = time.perf_counter()


def solve(n, m, profit, weight, capacity, time_limit=None, threads=1, history=None):
    model = cp.CpoModel()
    where = cp.integer_var_list(n, 0, 1)
    load = [[cp.integer_var(0, capacity[i]), cp.integer_var(0)] for i in range(m)]

    for i in range(m):
        model.add(cp.pack(load[i], where, weight[i]))

    model.add(cp.maximize(cp.sum((where[i] == 0) * profit[i] for i in range(n))))

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
        cost = result.get_objective_value()
        solution = []

        for i in range(n):
            if result[where[i]] == 0:
                solution.append(i)

        print(solution)
        print("cost: {}".format(cost))
        validation_result = read_mdkp.validate_mdkp(
            m, profit, weight, capacity, solution, cost
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
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    n, m, profit, weight, capacity = read_mdkp.read_mdkp(args.input)

    solve(
        n,
        m,
        profit,
        weight,
        capacity,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
    )
