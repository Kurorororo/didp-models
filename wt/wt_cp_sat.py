import argparse
import time

import read_single_machine_scheduling
from ortools.sat.python import cp_model

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

    model = cp_model.CpModel()

    s = [model.new_int_var(0, ub - processing_times[j], f"s[{j}]") for j in jobs]
    x = [
        model.new_fixed_size_interval_var(s[j], processing_times[j], f"x[{j}]")
        for j in jobs
    ]
    t = [model.new_int_var(0, ub - due_dates[j], f"t[{j}]") for j in jobs]

    model.add_no_overlap(x)

    # Precedence
    for k in jobs:
        for j in before[k]:
            model.add(s[j] + processing_times[j] <= s[k])

    for j in jobs:
        model.add_max_equality(t[j], [0, s[j] + processing_times[j] - due_dates[j]])

    model.minimize(sum(weights[j] * t[j] for j in jobs))

    solver = cp_model.CpSolver()

    solver.parameters.log_search_progress = verbose

    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit

    if threads is not None:
        solver.parameters.num_search_workers = threads

    status = solver.Solve(model)
    cost = None
    is_optimal = status == cp_model.OPTIMAL or status == cp_model.INFEASIBLE
    best_bound = solver.BestObjectiveBound()

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        start_times = [(solver.Value(s[j]), j) for j in jobs]
        solution = [j for _, j in sorted(start_times)]
        cost = solver.ObjectiveValue()
        gap = (cost - best_bound) / cost
    elif status == cp_model.INFEASIBLE:
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
        print(f"cost: {cost}")

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
                print(f"optimal cost: {cost}")
            else:
                if gap is not None:
                    print(f"gap: {gap}")

                if best_bound is not None:
                    print(f"best bound: {best_bound}")
        else:
            print("The solution is invalid")
