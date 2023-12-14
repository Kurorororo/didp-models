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
        name = "close {}".format(i)
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
    solver_name,
    history,
    time_limit=None,
    seed=2023,
    initial_beam_size=1,
    threads=1,
    parallel_type=0,
):
    if solver_name == "LNBS":
        if parallel_type == 2:
            parallelization_method = dp.BeamParallelizationMethod.Sbs
        elif parallel_type == 1:
            parallelization_method = dp.BeamParallelizationMethod.Hdbs1
        else:
            parallelization_method = dp.BeamParallelizationMethod.Hdbs2

        solver = dp.LNBS(
            model,
            f_operator=dp.FOperator.Max,
            parallelization_method=parallelization_method,
            threads=threads,
            time_limit=time_limit,
            quiet=False,
        )
    elif solver_name == "DD-LNS":
        solver = dp.DDLNS(
            model,
            f_operator=dp.FOperator.Max,
            time_limit=time_limit,
            quiet=False,
            seed=seed,
        )
    elif solver_name == "FR":
        solver = dp.ForwardRecursion(model, time_limit=time_limit, quiet=False)
    elif solver_name == "BrFS":
        solver = dp.BreadthFirstSearch(
            model, f_operator=dp.FOperator.Max, time_limit=time_limit, quiet=False
        )
    elif solver_name == "CAASDy":
        solver = dp.CAASDy(
            model, f_operator=dp.FOperator.Max, time_limit=time_limit, quiet=False
        )
    elif solver_name == "DFBB":
        solver = dp.DFBB(
            model, f_operator=dp.FOperator.Max, time_limit=time_limit, quiet=False
        )
    elif solver_name == "CBFS":
        solver = dp.CBFS(
            model, f_operator=dp.FOperator.Max, time_limit=time_limit, quiet=False
        )
    elif solver_name == "ACPS":
        solver = dp.ACPS(
            model, f_operator=dp.FOperator.Max, time_limit=time_limit, quiet=False
        )
    elif solver_name == "APPS":
        solver = dp.APPS(
            model, f_operator=dp.FOperator.Max, time_limit=time_limit, quiet=False
        )
    elif solver_name == "DBDFS":
        solver = dp.DBDFS(
            model, f_operator=dp.FOperator.Max, time_limit=time_limit, quiet=False
        )
    else:
        if parallel_type == 2:
            parallelization_method = dp.BeamParallelizationMethod.Sbs
        elif parallel_type == 1:
            parallelization_method = dp.BeamParallelizationMethod.Hdbs1
        else:
            parallelization_method = dp.BeamParallelizationMethod.Hdbs2

        solver = dp.CABS(
            model,
            initial_beam_size=initial_beam_size,
            threads=threads,
            parallelization_method=parallelization_method,
            time_limit=time_limit,
            quiet=False,
        )

    if solver_name == "FR":
        solution = solver.search()
    else:
        with open(history, "w") as f:
            is_terminated = False

            while not is_terminated:
                solution, is_terminated = solver.search_next()

                if solution.cost is not None:
                    f.write(
                        "{}, {}\n".format(time.perf_counter() - start, solution.cost)
                    )
                    f.flush()

    print("Search time: {}s".format(solution.time))
    print("Expanded: {}".format(solution.expanded))
    print("Generated: {}".format(solution.generated))

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
    parser.add_argument("--config", default="CABS", type=str)
    parser.add_argument("--seed", default=2023, type=int)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--initial-beam-size", default=1, type=int)
    parser.add_argument("--parallel-type", default=0, type=int)
    args = parser.parse_args()

    item_to_patterns, pattern_to_items = read_mosp.read(args.input)
    model, name_to_item = create_model(item_to_patterns, pattern_to_items)
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_item,
        args.config,
        args.history,
        time_limit=args.time_out,
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
        parallel_type=args.parallel_type,
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

            validation_result = read_mosp.validate(
                item_to_patterns, pattern_to_items, solution, cost
            )

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
