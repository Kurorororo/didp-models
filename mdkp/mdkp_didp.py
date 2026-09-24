#!/usr/bin/env python3
"""Multidimensional knapsack with one fractional-knapsack bound per dimension."""

import argparse
import math
import time

import didppy as dp
import read_mdkp


def create_model(n, m, profit, weight, capacity, *, epsilon=1e-6, blind=False):
    if not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("epsilon must be finite and nonnegative")
    if any(c < 0 for c in capacity) or any(w < 0 for row in weight for w in row):
        raise ValueError("Capacities and weights must be nonnegative")
    model = dp.Model(maximize=True)
    item = model.add_object_type(number=n + 1)
    j = model.add_element_var(object_type=item, target=0, name="next_item")
    r = [model.add_int_resource_var(target=c, less_is_better=False) for c in capacity]
    p = model.add_int_table(profit + [0])
    w = [model.add_int_table(row + [0]) for row in weight]
    model.add_base_case([j == n])
    model.add_transition(
        dp.Transition(
            name="pack",
            cost=p[j] + dp.IntExpr.state_cost(),
            effects=[(j, j + 1)] + [(r[i], r[i] - w[i][j]) for i in range(m)],
            preconditions=[j < n] + [r[i] >= w[i][j] for i in range(m)],
        )
    )
    model.add_transition(
        dp.Transition(
            name="ignore",
            cost=dp.IntExpr.state_cost(),
            effects=[(j, j + 1)],
            preconditions=[j < n],
        )
    )
    if not blind:
        rewards = model.add_int_table([max(0, v) for v in profit] + [0])
        suffix = model.add_set_table(
            [list(range(i, n)) for i in range(n + 1)], object_type=item
        )
        remaining = model.add_set_state_fun(suffix[j], name="remaining_items")
        model.add_dual_bound(rewards[remaining])
        x = model.add_local_var()
        for i in range(m):
            free = remaining.filter(x, w[i][x] == 0)
            positive = remaining.filter(x, w[i][x] > 0)
            model.add_dual_bound(
                math.floor(
                    rewards[free]
                    + dp.fractional_knapsack(positive, r[i], rewards, w[i])
                    + epsilon
                )
            )
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--config", choices=["CAASDy", "CABS", "LNBS"], default="CABS")
    parser.add_argument("--time-out", type=float, default=1800)
    parser.add_argument("--history", default="history.csv")
    parser.add_argument("--seed", type=int, default=2023)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--initial-beam-size", type=int, default=1)
    parser.add_argument("--epsilon", type=float, default=1e-6)
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()
    start = time.perf_counter()
    n, m, profit, weight, capacity = read_mdkp.read_mdkp(args.input)
    model = create_model(
        n, m, profit, weight, capacity, epsilon=args.epsilon, blind=args.blind
    )
    options = dict(time_limit=args.time_out, quiet=False)
    if args.config == "CAASDy":
        solver = dp.CAASDy(model, **options)
    elif args.config == "CABS":
        solver = dp.CABS(
            model,
            initial_beam_size=args.initial_beam_size,
            threads=args.threads,
            **options,
        )
    else:
        solver = dp.LNBS(
            model,
            initial_beam_size=args.initial_beam_size,
            threads=args.threads,
            seed=args.seed,
            **options,
        )
    with open(args.history, "w") as file:
        terminated = False
        while not terminated:
            solution, terminated = solver.search_next()
            if solution.cost is not None:
                file.write(f"{time.perf_counter() - start}, {solution.cost}\n")
                file.flush()
    print(f"Best bound: {solution.best_bound}")
    if solution.cost is not None:
        packed = [i for i, t in enumerate(solution.transitions) if t.name == "pack"]
        print(packed)
        print(f"Cost: {solution.cost}; optimal: {solution.is_optimal}")
        if not read_mdkp.validate_mdkp(
            m, profit, weight, capacity, packed, solution.cost
        ):
            raise RuntimeError("Invalid solution")
        print("The solution is valid.")
    else:
        print(
            "The problem is infeasible."
            if solution.is_infeasible
            else "No solution found."
        )
