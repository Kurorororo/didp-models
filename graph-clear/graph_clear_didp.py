#!/usr/bin/env python3

import argparse
import time

import didppy as dp
import read_graph_clear

start = time.perf_counter()


def create_model(n, node_weights, edge_weights):
    model = dp.Model()
    node = model.add_object_type(n)
    clean = model.add_set_var(node, [])
    all_nodes = model.create_set_const(node, [i for i in range(n)])
    a = model.add_int_table(node_weights)
    b = model.add_int_table(
        [
            [
                edge_weights[i, j]
                if (i, j) in edge_weights
                else edge_weights[j, i]
                if (j, i) in edge_weights
                else 0
                for j in range(n)
            ]
            for i in range(n)
        ]
    )

    model.add_base_case([all_nodes <= clean])

    name_to_node = {}

    for i in range(n):
        name = "sweep {}".format(i)
        name_to_node[name] = i
        t = dp.Transition(
            name=name,
            cost=dp.max(
                dp.IntExpr.state_cost(),
                a[i] + b[i, all_nodes] + b[clean, clean.complement().remove(i)],
            ),
            effects=[(clean, clean.add(i))],
            preconditions=[~clean.contains(i)],
        )
        model.add_transition(t)

    model.add_dual_bound(0)

    return model, name_to_node


def solve(
    model,
    name_to_node,
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
        sequence = []

        for t in solution.transitions:
            sequence.append(name_to_node[t.name])

        return sequence, solution.cost, solution.best_bound, solution.is_optimal, False


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

    n, a, b = read_graph_clear.read(args.input)
    model, name_to_node = create_model(n, a, b)
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_node,
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
            print(solution)
            print("cost: {}".format(cost))

            if is_optimal:
                print("optimal cost: {}".format(cost))

            validation_result = read_graph_clear.validate(n, a, b, solution, cost)

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
