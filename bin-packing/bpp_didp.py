#!/usr/bin/env python3

import argparse
import math
import time

import didppy as dp
import read_bpp

start = time.perf_counter()


def create_model(n, c, weights):
    model = dp.Model()

    item = model.add_object_type(n)
    unpacked = model.add_set_var(item, [i for i in range(n)])
    residual = model.add_int_resource_var(0, less_is_better=False)
    bin_number = model.add_element_resource_var(item, 0, less_is_better=True)

    weight_table = model.add_int_table(weights)
    lb2_weight1 = model.add_int_table(
        [1 if weights[i] > c / 2 else 0 for i in range(n)]
    )
    lb2_weight2 = model.add_float_table(
        [0.5 if weights[i] == c / 2 else 0 for i in range(n)]
    )
    lb3_weight = model.add_float_table(
        [
            (
                1.0
                if weights[i] > c * 2 / 3
                else (
                    2 / 3 // 0.001 / 1000
                    if weights[i] == c * 2 / 3
                    else (
                        0.5
                        if weights[i] > c / 3
                        else 1 / 3 // 0.001 / 1000
                        if weights[i] == c / 3
                        else 0.0
                    )
                )
            )
            for i in range(n)
        ]
    )
    model.add_base_case([unpacked.is_empty()])

    name_to_item = {}

    x = model.add_local_var()
    no_available_item = model.add_bool_state_fun(
        unpacked.all(x, weight_table[x] > residual)
    )

    for i in range(n):
        name = f"pack {i}"
        name_to_item[name] = i
        t = dp.Transition(
            name=name,
            cost=dp.IntExpr.state_cost(),
            effects=[
                (unpacked, unpacked.remove(i)),
                (residual, residual - weight_table[i]),
            ],
            preconditions=[
                unpacked.contains(i),
                weight_table[i] <= residual,
                bin_number <= i + 1,
            ],
        )
        model.add_transition(t)

        name = f"open a new bin and pack {i}"
        name_to_item[name] = i
        ft = dp.Transition(
            name=name,
            cost=dp.IntExpr.state_cost() + 1,
            preconditions=[
                bin_number <= i,
                unpacked.contains(i),
                no_available_item,
            ],
            effects=[
                (unpacked, unpacked.remove(i)),
                (residual, c - weight_table[i]),
                (bin_number, bin_number + 1),
            ],
        )
        model.add_transition(ft, forced=True)

    model.add_dual_bound(math.ceil((weight_table[unpacked] - residual) / c))
    model.add_dual_bound(
        lb2_weight1[unpacked]
        + math.ceil(lb2_weight2[unpacked])
        - (residual >= c / 2).if_then_else(1, 0)
    )
    model.add_dual_bound(
        math.ceil(lb3_weight[unpacked]) - (residual >= c / 3).if_then_else(1, 0)
    )

    return model, name_to_item


def solve(
    model,
    name_to_item,
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
        assignment = []

        for t in solution.transitions:
            if "open a new bin" in t.name:
                assignment.append([])

            assignment[-1].append(name_to_item[t.name])

        return (
            assignment,
            solution.cost,
            solution.best_bound,
            solution.is_optimal,
            False,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-out", default=1800, type=int)
    parser.add_argument("--history", default="history.csv", type=str)
    parser.add_argument("--config", choices=["CAASDy", "CABS", "LNBS"], default="CABS")
    parser.add_argument("--seed", default=2023, type=int)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--initial-beam-size", default=1, type=int)
    args = parser.parse_args()

    n, c, weights = read_bpp.read(args.input)
    model, name_to_item = create_model(n, c, weights)
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_item,
        args.config,
        args.history,
        time_limit=args.time_out,
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
    )

    if is_infeasible:
        print("The problem is infeasible.")
    else:
        print(f"best bound: {bound}")

        if cost is not None:
            print(solution)
            print(f"cost: {cost}")

            if is_optimal:
                print(f"optimal cost: {cost}")

            validation_result = read_bpp.validate(n, c, weights, solution, cost)

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
