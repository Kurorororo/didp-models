#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp

import read_mosp


start = time.perf_counter()


def solve(item_to_patterns, pattern_to_items, time_limit=None, threads=1, history=None):
    n_items = len(item_to_patterns)
    n_patterns = len(pattern_to_items)

    model = cp.CpoModel()
    patterns = cp.interval_var_list(
        n_patterns, start=(0, n_patterns - 1), end=(1, n_patterns), size=1
    )
    item_to_patterns_var = [
        [patterns[j] for j in item_to_patterns[i]] for i in range(n_items)
    ]
    items = [
        cp.interval_var(
            start=(0, cp.INTERVAL_MAX),
            end=(0, n_patterns),
            size=(len(item_to_patterns[i]), n_patterns),
        )
        for i in range(n_items)
    ]
    model.add(cp.no_overlap(patterns))
    for i in range(n_items):
        model.add(cp.span(items[i], item_to_patterns_var[i]))
    c = cp.integer_var()
    model.add(c >= cp.sum(cp.pulse(items[i], 1) for i in range(n_items)))
    model.add(cp.minimize(c))

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
        scheduled = set()
        solution = []
        while len(scheduled) < len(patterns):
            min_s = -1
            argmin = -1
            for j in range(n_patterns):
                if j not in scheduled:
                    s = result[patterns[j]].start
                    if min_s == -1 or s < min_s:
                        min_s = s
                        argmin = j
            scheduled.add(argmin)
            solution.append(argmin)

        cost = round(result.get_objective_value())
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_mosp.validate(
            item_to_patterns, pattern_to_items, solution, cost
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
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    item_to_patterns, pattern_to_items = read_mosp.read(args.input)
    solve(
        item_to_patterns,
        pattern_to_items,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
    )
