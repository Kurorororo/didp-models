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
    if not add_time_var:
        current_time = model.add_int_state_fun(
            processing_time[scheduled], name="current_time"
        )

    model.add_base_case([scheduled == all_jobs])

    name_to_job = {}
    state_cost = dp.IntExpr.state_cost()

    for j in range(n):
        name = f"schedule {j}"
        name_to_job[name] = j
        effects = [(scheduled, scheduled.add(j))]

        if add_time_var:
            effects.append((current_time, current_time + processing_time[j]))

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


def solve(
    model,
    name_to_job,
    solver_name,
    history,
    time_limit=None,
    seed=2023,
    initial_beam_size=1,
    threads=1,
):
    options = dict(time_limit=time_limit, quiet=False)
    if solver_name == "CAASDy":
        solver = dp.CAASDy(model, **options)
    elif solver_name == "CABS":
        solver = dp.CABS(
            model, initial_beam_size=initial_beam_size, threads=threads, **options
        )
    elif solver_name == "LNBS":
        solver = dp.LNBS(
            model,
            initial_beam_size=initial_beam_size,
            threads=threads,
            seed=seed,
            **options,
        )
    else:
        raise ValueError(f"Unknown solver: {solver_name}")

    with open(history, "w") as f:
        is_terminated = False

        while not is_terminated:
            solution, is_terminated = solver.search_next()

            if solution.cost is not None:
                f.write(f"{time.perf_counter() - start}, {solution.cost}\n")
                f.flush()

    print(f"Search time: {solution.time}s")
    print(f"Expanded: {solution.expanded}")
    print(f"Generated: {solution.generated}")

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
    parser.add_argument("--config", choices=["CAASDy", "CABS", "LNBS"], default="CABS")
    parser.add_argument("--seed", default=2023, type=int)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--initial-beam-size", default=1, type=int)
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
        args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
    )

    if is_infeasible:
        print("The problem is infeasible.")
    else:
        print(f"best bound: {bound}")

        if cost is not None:
            print(" ".join(map(str, solution)))
            print(f"cost: {cost}")

            if is_optimal:
                print(f"optimal cost: {cost}")

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
