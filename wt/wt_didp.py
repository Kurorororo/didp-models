#!/usr/bin/env python3

import argparse
import time

import didppy as dp
import read_single_machine_scheduling

start = time.perf_counter()


def create_model(processing_times, due_dates, weights, before, add_time_var=False):
    n = len(processing_times)

    model = dp.Model()

    job = model.add_object_type(number=n)
    scheduled = model.add_set_var(object_type=job, target=[])

    if add_time_var:
        current_time = model.add_int_var(target=0)

    all_jobs = model.create_set_const(object_type=job, value=list(range(n)))

    processing_time = model.add_int_table(processing_times)
    due_date = model.add_int_table(due_dates)
    weight = model.add_int_table(weights)
    predecessors = model.add_set_table(before, object_type=job)

    model.add_base_case([scheduled == all_jobs])

    name_to_job = {}
    state_cost = dp.IntExpr.state_cost()

    for j in range(n):
        name = "schedule {}".format(j)
        name_to_job[name] = j
        effects = [(scheduled, scheduled.add(j))]

        if add_time_var:
            effects.append((current_time, current_time + processing_time[j]))
        else:
            current_time = processing_time[scheduled]

        tardiness = dp.max(0, current_time + processing_time[j] - due_date[j])
        schedule = dp.Transition(
            name=name,
            cost=weight[j] * tardiness + state_cost,
            effects=effects,
            preconditions=[~scheduled.contains(j), predecessors[j].issubset(scheduled)],
        )
        model.add_transition(schedule)

    model.add_dual_bound(0)

    return model, name_to_job


def solve(model, name_to_job, solver_name, history, time_limit=None):
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
        permutation = [name_to_job[t.name] for t in solution.transitions]

        return (
            permutation,
            solution.cost,
            solution.best_bound,
            solution.is_optimal,
            False,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--add-time-var", action="store_true")
    parser.add_argument("--time-out", default=1800, type=int)
    parser.add_argument("--history", default="history.csv", type=str)
    parser.add_argument("--config", default="CABS", type=str)
    args = parser.parse_args()

    (
        processing_times,
        due_dates,
        weights,
    ) = read_single_machine_scheduling.read_wt(args.input)
    original_before = None
    before, _ = read_single_machine_scheduling.extract_precedence_for_wt(
        processing_times, due_dates, weights
    )

    model, name_to_job = create_model(
        processing_times, due_dates, weights, before, add_time_var=args.add_time_var
    )
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_job,
        args.config,
        args.history,
        args.time_out,
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

            validation_result, _ = read_single_machine_scheduling.verify_wt(
                solution,
                processing_times,
                due_dates,
                weights,
                cost=cost,
            )

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
