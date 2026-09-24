#!/usr/bin/env python3

import argparse
import time

import didppy as dp
import read_mosp

start = time.perf_counter()


def create_model(item_to_patterns, pattern_to_items):
    m = len(item_to_patterns)
    item_to_neighbors = read_mosp.compute_item_to_neighbors(
        item_to_patterns, pattern_to_items
    )

    model = dp.Model()
    item = model.add_object_type(m)
    remaining = model.add_set_var(item, [i for i in range(m)])
    opened = model.add_set_var(item, [])
    neighbors = model.add_set_table(item_to_neighbors, object_type=item)

    model.add_base_case([remaining.is_empty()])

    name_to_item = {}

    for i in range(m):
        name = f"close {i}"
        name_to_item[name] = i
        t = dp.Transition(
            name=name,
            cost=dp.max(
                dp.IntExpr.state_cost(),
                ((opened & remaining) | (neighbors[i] - opened)).len(),
            ),
            effects=[(remaining, remaining.remove(i)), (opened, opened | neighbors[i])],
            preconditions=[remaining.contains(i)],
        )
        model.add_transition(t)

    model.add_dual_bound(0)

    return model, name_to_item


def solve(
    model,
    name_to_item,
    item_to_patterns,
    solver_name,
    history,
    time_limit=None,
    seed=2023,
    initial_beam_size=1,
    threads=1,
):
    options = dict(time_limit=time_limit, quiet=False, f_operator=dp.FOperator.Max)
    if solver_name == "CAASDy":
        solver = dp.CAASDy(model, **options)
    elif solver_name == "CABS":
        solver = dp.CABS(
            model, initial_beam_size=initial_beam_size, threads=threads, **options
        )
    elif solver_name == "LNBS":
        solver = dp.LNBS(
            model,
            f_operator=dp.FOperator.Max,
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
        pattern_sequence = []
        produced = set()

        for t in solution.transitions:
            item = name_to_item[t.name]

            for pattern in item_to_patterns[item]:
                if pattern not in produced:
                    pattern_sequence.append(pattern)
                    produced.add(pattern)

        return (
            pattern_sequence,
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

    item_to_patterns, pattern_to_items = read_mosp.read(args.input)
    model, name_to_item = create_model(item_to_patterns, pattern_to_items)
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_item,
        item_to_patterns,
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
            print(" ".join(map(str, solution)))
            print(f"cost: {cost}")

            if is_optimal:
                print(f"optimal cost: {cost}")

            validation_result = read_mosp.validate(
                item_to_patterns, pattern_to_items, solution, cost
            )

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
