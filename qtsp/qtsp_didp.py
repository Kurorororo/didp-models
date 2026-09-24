#!/usr/bin/env python3
"""The original exact QTSP formulation with both closing triple costs."""

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import didppy as dp
import read_qtsp


def cost_minima(costs):
    n = len(costs)
    if n < 3:
        raise ValueError("QTSP requires at least three vertices")
    incoming, middle, outgoing = [[math.inf] * n for _ in range(3)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if len({i, j, k}) == 3:
                    value = costs[i][j][k]
                    if not isinstance(value, int) or value < 0:
                        raise ValueError("Costs must be nonnegative integers")
                    incoming[k] = min(incoming[k], value)
                    middle[j] = min(middle[j], value)
                    outgoing[i] = min(outgoing[i], value)
    return incoming, middle, outgoing


def create_model(n, costs, *, blind=False):
    model = dp.Model()
    node = model.add_object_type(number=n)
    u = model.add_set_var(object_type=node, target=list(range(1, n)), name="unvisited")
    i = model.add_element_var(object_type=node, target=0, name="previous")
    j = model.add_element_var(object_type=node, target=0, name="current")
    f = model.add_element_var(object_type=node, target=0, name="first")
    c = model.add_int_table(costs)
    names = {}
    for k in range(1, n):
        name = f"first visit {k}"
        names[name] = k
        model.add_transition(
            dp.Transition(
                name=name,
                cost=dp.IntExpr.state_cost(),
                effects=[(u, u.remove(k)), (j, k), (f, k)],
                preconditions=[j == 0],
            )
        )
        name = f"visit {k}"
        names[name] = k
        model.add_transition(
            dp.Transition(
                name=name,
                cost=c[i, j, k] + dp.IntExpr.state_cost(),
                effects=[(u, u.remove(k)), (i, j), (j, k)],
                preconditions=[j != 0, u.contains(k)],
            )
        )
    model.add_base_case([u.is_empty()], cost=c[i, j, 0] + c[j, 0, f])
    if not blind:
        cin, cmid, cout = [model.add_int_table(v) for v in cost_minima(costs)]
        # Set unions avoid counting vertex 0 twice at the root.
        model.add_dual_bound(cin[u.add(0).add(f)])
        model.add_dual_bound(cmid[u.add(0).add(j)])
        model.add_dual_bound(cout[u.add(i).add(j)])
    return model, names


def create_solver(
    model,
    solver_name,
    time_limit=None,
    primal_bound=None,
    quiet=True,
    seed=2023,
    initial_beam_size=1,
    threads=1,
):
    options = dict(time_limit=time_limit, primal_bound=primal_bound, quiet=quiet)
    if solver_name == "CAASDy":
        return dp.CAASDy(model, **options)
    if solver_name == "CABS":
        return dp.CABS(
            model, initial_beam_size=initial_beam_size, threads=threads, **options
        )
    if solver_name == "LNBS":
        return dp.LNBS(
            model,
            initial_beam_size=initial_beam_size,
            threads=threads,
            seed=seed,
            **options,
        )
    raise ValueError(f"Unknown solver: {solver_name}")


@dataclass
class Result:
    tour: list | None = None
    cost: int | None = None
    best_bound: int = 0
    is_optimal: bool = False
    is_infeasible: bool = False
    elapsed: float = 0.0
    expanded: int = 0
    generated: int = 0
    history: list = field(default_factory=list)


def check_time_limit(time_limit):
    if time_limit is not None and (not math.isfinite(time_limit) or time_limit < 0):
        raise ValueError("time_limit must be finite and nonnegative")


def record(result, costs, tour, cost, start, source):
    if not read_qtsp.validate_tour(costs, tour, cost):
        raise ValueError("Invalid Hamiltonian tour or objective")
    if result.cost is None or cost < result.cost:
        result.tour, result.cost = tour, cost
        result.history.append(
            dict(time=time.perf_counter() - start, cost=cost, source=source)
        )


def solve(
    n,
    costs,
    solver_name="CABS",
    time_limit=30,
    *,
    seed_tour=True,
    blind=False,
    quiet=True,
    seed=2023,
    initial_beam_size=1,
    threads=1,
):
    check_time_limit(time_limit)
    start = time.perf_counter()
    deadline = math.inf if time_limit is None else start + time_limit
    result = Result()
    if seed_tour and time.perf_counter() < deadline:
        tour, cost = read_qtsp.insertion_tour(costs)
        record(result, costs, tour, cost, start, "insertion")
    if time.perf_counter() < deadline:
        model, names = create_model(n, costs, blind=blind)
        result.best_bound = max(
            (h.eval(model.target_state, model) for h in model.dual_bounds), default=0
        )
        if time.perf_counter() < deadline and (
            result.cost is None or result.best_bound < result.cost
        ):
            solver = create_solver(
                model,
                solver_name,
                None if time_limit is None else deadline - time.perf_counter(),
                None if result.cost is None else result.cost + 1,
                quiet,
                seed=seed,
                initial_beam_size=initial_beam_size,
                threads=threads,
            )
            terminated = False
            while not terminated:
                solution, terminated = solver.search_next()
                if solution.best_bound is not None:
                    result.best_bound = max(result.best_bound, solution.best_bound)
                if solution.cost is not None:
                    tour = [0] + [names[t.name] for t in solution.transitions] + [0]
                    record(result, costs, tour, solution.cost, start, "search")
                    if solution.is_optimal:
                        result.best_bound = max(result.best_bound, solution.cost)
                if result.cost is not None and result.best_bound >= result.cost:
                    break
            result.expanded, result.generated = solution.expanded, solution.generated
            result.is_infeasible = solution.is_infeasible and result.cost is None
    result.is_optimal = result.cost is not None and result.best_bound >= result.cost
    result.elapsed = time.perf_counter() - start
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--kind", choices=["angle", "angle-distance"], default="angle")
    parser.add_argument("--decimals", type=int, default=2)
    parser.add_argument("--config", choices=["CAASDy", "CABS", "LNBS"], default="CABS")
    parser.add_argument("--time-out", type=float, default=30)
    parser.add_argument("--no-seed", action="store_true")
    parser.add_argument("--seed", type=int, default=2023)
    parser.add_argument("--initial-beam-size", type=int, default=1)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--blind", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--history", type=Path)
    args = parser.parse_args()
    n, costs = read_qtsp.load_instance(args.input, args.kind, args.decimals)
    result = solve(
        n,
        costs,
        args.config,
        args.time_out,
        seed_tour=not args.no_seed,
        blind=args.blind,
        quiet=not args.verbose,
        seed=args.seed,
        initial_beam_size=args.initial_beam_size,
        threads=args.threads,
    )
    print(f"Tour: {result.tour}")
    print(f"Cost: {None if result.cost is None else result.cost / 10**args.decimals}")
    print(f"Lower bound: {result.best_bound / 10**args.decimals}")
    print(f"Optimal: {result.is_optimal}; time: {result.elapsed:.6f}s")
    if args.json:
        args.json.write_text(json.dumps(asdict(result), indent=2) + "\n")
    if args.history:
        args.history.write_text(
            "time,cost,source\n"
            + "".join(
                f"{r['time']},{r['cost']},{r['source']}\n" for r in result.history
            )
        )
