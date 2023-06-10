#!/usr/bin/env python3

import argparse
import time

import gurobipy as gp

import read_single_machine_scheduling


start = time.perf_counter()


def get_callback(file):
    def dump_solution(model, where):
        if where == gp.GRB.Callback.MIPSOL:
            file.write(
                "{}, {}\n".format(
                    time.perf_counter() - start,
                    model.cbGet(gp.GRB.Callback.MIPSOL_OBJ),
                )
            )

    return dump_solution


def solve_positional(
    processing_times,
    due_dates,
    weights,
    before,
    valid_inequalities=False,
    use_ub=False,
    feasibility_tol=1e-2,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    jobs = list(range(len(processing_times)))
    n = len(jobs)
    positions = list(range(len(processing_times)))
    big_m = sum(processing_times)

    sorted_jobs = [
        j for _, j in sorted([(p, j) for j, p in enumerate(processing_times)])
    ]

    job_to_order = [0 for _ in jobs]
    for i, j in enumerate(sorted_jobs):
        job_to_order[j] = i

    sorted_processing_times = [processing_times[j] for j in sorted_jobs]
    sorted_due_dates = [due_dates[j] for j in sorted_jobs]
    sorted_weights = [weights[j] for j in sorted_jobs]
    sorted_before = [{job_to_order[i] for i in before[j]} for j in sorted_jobs]

    model = gp.Model()

    gamma_ub = [sum(sorted_processing_times[n - i - 1 :]) for i in positions]

    if use_ub:
        gamma = model.addVars(positions, vtype=gp.GRB.CONTINUOUS, lb=0, ub=gamma_ub)
        c = model.addVars(jobs, vtype=gp.GRB.CONTINUOUS, lb=0, ub=big_m)
    else:
        gamma = model.addVars(positions, vtype=gp.GRB.CONTINUOUS, lb=0)
        c = model.addVars(jobs, vtype=gp.GRB.CONTINUOUS, lb=0)

    u = model.addVars(jobs, positions, vtype=gp.GRB.BINARY)
    t = model.addVars(jobs, vtype=gp.GRB.CONTINUOUS, lb=0, obj=sorted_weights)

    model.addConstrs(gp.quicksum(u[j, k] for k in positions) == 1 for j in jobs)
    model.addConstrs(gp.quicksum(u[j, k] for j in jobs) == 1 for k in positions)
    model.addConstr(
        gamma[0] >= gp.quicksum(sorted_processing_times[j] * u[j, 0] for j in jobs)
    )
    model.addConstrs(
        gamma[k]
        >= gamma[k - 1]
        + gp.quicksum(sorted_processing_times[j] * u[j, k] for j in jobs)
        for k in positions[1:]
    )
    model.addConstrs(t[j] >= c[j] - sorted_due_dates[j] for j in jobs)

    if valid_inequalities:
        pi = {
            (j, k): sum(sorted_processing_times[:k])
            if k <= j
            else sum(sorted_processing_times[:j])
            + sum(sorted_processing_times[j + 1 : k + 1])
            for j in jobs
            for k in positions
        }
        ro = {
            (j, k): sum(sorted_processing_times[k + 1 :])
            if k >= j
            else sum(sorted_processing_times[k:j])
            + sum(sorted_processing_times[j + 1 :])
            for j in jobs
            for k in positions
        }

        for k in positions:
            a = {
                (j, l): ro[j, n - k + l - 1]
                if l < k
                else sorted_processing_times[j] + pi[j, l - k - 1]
                if l > k
                else 0
                for j in jobs
                for l in jobs
            }
            model.addConstrs(
                c[j]
                >= gamma[k]
                - gp.quicksum(a[j, l] * u[j, l] for l in range(k))
                + gp.quicksum(a[j, l] * u[j, l] for l in range(k + 1, n))
                for j in jobs
            )

        model.addConstrs(
            c[j]
            >= sorted_processing_times[j]
            + gp.quicksum(pi[j, k] * u[j, k] for k in positions[1:])
            for j in jobs
        )
    else:
        if use_ub:
            model.addConstrs(
                c[j] >= gamma[k] - gamma_ub[k] * (1 - u[j, k])
                for j in jobs
                for k in positions
            )
        else:
            model.addConstrs(
                c[j] >= gamma[k] - big_m * (1 - u[j, k])
                for j in jobs
                for k in positions
            )

    # Precedence
    model.addConstrs(
        c[j] + sorted_processing_times[k] <= c[k]
        for k in jobs
        for j in sorted_before[k]
    )

    model.setParam("FeasibilityTol", feasibility_tol)
    model.setParam("Threads", threads)

    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)

    if not verbose:
        model.setParam("OutputFlag", 0)

    if history is None:
        model.optimize()
    else:
        with open(history, "w") as f:
            callback = get_callback(f)
            model.optimize(callback)

    status = model.getAttr("Status")
    sol_count = model.getAttr("SolCount")

    solution = None
    cost = None
    is_optimal = status == gp.GRB.OPTIMAL
    gap = None
    best_bound = None

    if status == gp.GRB.INFEASIBLE:
        print("infeasible")
    else:
        best_bound = model.getAttr("ObjBound")

    if sol_count > 0:
        cost = round(model.objVal)
        completion_times = sorted([(c[j].X, j) for j in jobs])
        solution = [j for _, j in completion_times]
        solution = [sorted_jobs[j] for j in solution]

    return solution, cost, is_optimal, gap, best_bound


def solve_time_index(
    processing_times,
    due_dates,
    weights,
    before,
    feasibility_tol=1e-2,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    jobs = list(range(len(processing_times)))
    horizon = sum(processing_times) + 1
    times = list(range(0, horizon))

    objective_weights = {
        (j, t): weights[j] * max(0, t + processing_times[j] - due_dates[j])
        for j in jobs
        for t in times
    }

    model = gp.Model()

    x = model.addVars(jobs, times, vtype=gp.GRB.BINARY, obj=objective_weights)

    model.addConstrs(
        gp.quicksum(x[j, t] for t in range(0, horizon - processing_times[j])) == 1
        for j in jobs
    )
    model.addConstrs(
        gp.quicksum(
            x[j, s] for j in jobs for s in range(max(0, t - processing_times[j]), t)
        )
        <= 1
        for t in times
    )

    # Precedence
    model.addConstrs(
        gp.quicksum(t * x[k, t] for t in range(0, horizon - processing_times[k]))
        >= gp.quicksum(
            (t + processing_times[j]) * x[j, t]
            for t in range(0, horizon - processing_times[j])
        )
        for k in jobs
        for j in before[k]
    )

    model.setParam("FeasibilityTol", feasibility_tol)
    model.setParam("Threads", threads)

    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)

    if not verbose:
        model.setParam("OutputFlag", 0)

    if history is None:
        model.optimize()
    else:
        with open(history, "w") as f:
            callback = get_callback(f)
            model.optimize(callback)

    status = model.getAttr("Status")
    sol_count = model.getAttr("SolCount")

    solution = None
    cost = None
    is_optimal = status == gp.GRB.OPTIMAL
    gap = None
    best_bound = None

    if status == gp.GRB.INFEASIBLE:
        print("infeasible")
    else:
        best_bound = model.getAttr("ObjBound")

    if sol_count > 0:
        cost = round(model.objVal)
        t = 0
        solution = []

        while t < horizon:
            for j in jobs:
                if x[j, t].X >= 0.5:
                    solution.append(j)
                    t += processing_times[j]
                    break
            else:
                t += 1

    return solution, cost, is_optimal, gap, best_bound


def solve_completion_time(
    processing_times,
    due_dates,
    weights,
    before,
    feasibility_tol=1e-2,
    use_ub=False,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    jobs = list(range(len(processing_times)))
    job_pairs = [
        (j, k)
        for j in jobs
        for k in jobs
        if j < k and j not in before[k] and k not in before[j]
    ]
    big_m = sum(processing_times)
    c_lb = [processing_times[j] for j in jobs]

    model = gp.Model()

    if use_ub:
        c = model.addVars(jobs, vtype=gp.GRB.CONTINUOUS, lb=c_lb, ub=big_m)
    else:
        c = model.addVars(jobs, vtype=gp.GRB.CONTINUOUS, lb=c_lb)

    y = model.addVars(job_pairs, vtype=gp.GRB.INTEGER)

    model.addConstrs(
        c[j] + processing_times[k] <= c[k] + big_m * (1 - y[j, k])
        for (j, k) in job_pairs
    )
    model.addConstrs(
        c[k] + processing_times[j] <= c[j] + big_m * y[j, k] for (j, k) in job_pairs
    )

    t = model.addVars(jobs, vtype=gp.GRB.CONTINUOUS, lb=0, obj=weights)
    model.addConstrs(t[j] >= c[j] - due_dates[j] for j in jobs)

    # Precedence
    model.addConstrs(
        c[j] + processing_times[k] <= c[k] for k in jobs for j in before[k]
    )

    model.setParam("FeasibilityTol", feasibility_tol)
    model.setParam("Threads", threads)

    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)

    if not verbose:
        model.setParam("OutputFlag", 0)

    if history is None:
        model.optimize()
    else:
        with open(history, "w") as f:
            callback = get_callback(f)
            model.optimize(callback)

    status = model.getAttr("Status")
    sol_count = model.getAttr("SolCount")

    solution = None
    cost = None
    is_optimal = status == gp.GRB.OPTIMAL
    gap = None
    best_bound = None

    if status == gp.GRB.INFEASIBLE:
        print("infeasible")
    else:
        best_bound = model.getAttr("ObjBound")

    if sol_count > 0:
        cost = round(model.objVal)
        completion_times = sorted([(c[j].X, j) for j in jobs])
        solution = [j for _, j in completion_times]

    return solution, cost, is_optimal, gap, best_bound


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--history", type=str)
    parser.add_argument("--precedence", action="store_true")
    parser.add_argument("--extract-precedence", action="store_true")
    parser.add_argument("--time-index", action="store_true")
    parser.add_argument("--completion-time", action="store_true")
    parser.add_argument("--valid-inequalities", action="store_true")
    parser.add_argument("--use-ub", action="store_true")
    parser.add_argument("--feasibility-tol", type=float, default=1e-2)
    args = parser.parse_args()

    if args.precedence:
        (
            processing_times,
            due_dates,
            weights,
            original_before,
            original_after,
        ) = read_single_machine_scheduling.read_wt_prec(args.input)

        if args.extract_precedence:
            before, _ = read_single_machine_scheduling.extract_precedence_for_wt_prec(
                processing_times, due_dates, weights, original_before, original_after
            )
        else:
            before = original_before
    else:
        (
            processing_times,
            due_dates,
            weights,
        ) = read_single_machine_scheduling.read_wt(args.input)
        original_before = None

        if args.extract_precedence:
            before, _ = read_single_machine_scheduling.extract_precedence_for_wt(
                processing_times, due_dates, weights
            )
        else:
            before = [set() for _ in range(len(processing_times))]

    if args.completion_time:
        solution, cost, is_optimal, gap, best_bound = solve_completion_time(
            processing_times,
            due_dates,
            weights,
            before,
            use_ub=args.use_ub,
            threads=args.threads,
            time_limit=args.time_out,
            verbose=args.verbose,
            history=args.history,
        )
    elif args.time_index:
        solution, cost, is_optimal, gap, best_bound = solve_time_index(
            processing_times,
            due_dates,
            weights,
            before,
            threads=args.threads,
            time_limit=args.time_out,
            verbose=args.verbose,
            history=args.history,
        )
    else:
        solution, cost, is_optimal, gap, best_bound = solve_positional(
            processing_times,
            due_dates,
            weights,
            before,
            valid_inequalities=args.valid_inequalities,
            use_ub=args.use_ub,
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
            # It is possible that the objective cost does not match the actual cost
            # as the constraints are inequalities.
            print("The solution is invalid.")
