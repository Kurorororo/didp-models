#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp

import read_single_machine_scheduling


start = time.perf_counter()


def solve(
    processing_times,
    due_dates,
    weights,
    before,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    jobs = list(range(len(processing_times)))
    ub = sum(processing_times)

    model = cp.CpoModel()

    x = [
        cp.interval_var(
            start=(0, ub - processing_times[j]), end=(0, ub), length=processing_times[j]
        )
        for j in jobs
    ]
    pi = cp.sequence_var(x)
    model.add(cp.no_overlap(pi))

    # Precedence
    for k in jobs:
        for j in before[k]:
            model.add(cp.before(pi, x[j], x[k]))

    model.add(
        cp.minimize(
            cp.sum(
                [weights[j] * cp.max(0, cp.end_of(x[j]) - due_dates[j]) for j in jobs]
            )
        )
    )

    if args.history is None:
        if verbose:
            result = model.solve(TimeLimit=time_limit, Workers=threads)
        else:
            result = model.solve(
                TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
            )
    else:
        if verbose:
            solver = cp.CpoSolver(
                model,
                TimeLimit=time_limit,
                Workers=threads,
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

    solution = None
    cost = None
    is_optimal = None
    gap = None
    best_bound = None

    if result.is_solution():
        completion_times = [(result[x[j]].end, j) for j in jobs]
        solution = [j for _, j in sorted(completion_times)]
        cost = round(result.get_objective_value())

        is_optimal = result.is_solution_optimal()
        gap = result.get_objective_gap()
        best_bound = result.get_objective_bound()
    elif result.get_solve_status() == "Infeasible":
        print("The problem is infeasible.")

    return solution, cost, is_optimal, gap, best_bound


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--history", type=str)
    parser.add_argument("--precedence", action="store_true")
    parser.add_argument("--not-extract-precedence", action="store_true")
    args = parser.parse_args()

    if args.precedence:
        (
            processing_times,
            due_dates,
            weights,
            original_before,
            original_after,
        ) = read_single_machine_scheduling.read_wt_prec(args.input)

        if args.not_extract_precedence:
            before = original_before
        else:
            before, _ = read_single_machine_scheduling.extract_precedence_for_wt_prec(
                processing_times, due_dates, weights, original_before, original_after
            )
    else:
        (
            processing_times,
            due_dates,
            weights,
        ) = read_single_machine_scheduling.read_wt(args.input)
        original_before = None

        if args.not_extract_precedence:
            before = [set() for _ in range(len(processing_times))]
        else:
            before, _ = read_single_machine_scheduling.extract_precedence_for_wt(
                processing_times, due_dates, weights
            )

    solution, cost, is_optimal, gap, best_bound = solve(
        processing_times,
        due_dates,
        weights,
        before,
        threads=args.threads,
        time_limit=args.time_out,
        verbose=args.verbose,
        history=args.history,
    )

    if solution is not None:
        print(solution)
        print("cost: {}".format(cost))

        validation_result, cost = read_single_machine_scheduling.verify_wt(
            solution,
            processing_times,
            due_dates,
            weights,
            cost=cost,
            before=original_before,
        )

        if validation_result:
            print("The solution is valid.")
            if is_optimal:
                print("optimal cost: {}".format(cost))
            else:
                if gap is not None:
                    print("gap: {}".format(gap))

                if best_bound is not None:
                    print("best bound: {}".format(best_bound))
        else:
            print("The solution is invalid")
