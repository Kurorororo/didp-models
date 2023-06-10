#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp

import read_tsplib
from mpdtsp_util import (
    compute_precedence,
    compute_predecessors_and_successors,
    check_edge,
    compute_not_inferred_precedence,
)


start = time.perf_counter()


def compute_ub(nodes, edges):
    if any(all((i, j) not in edges for j in nodes) for i in nodes[:-1]):
        return -1

    return sum(max(edges[i, j] for j in nodes if (i, j) in edges) for i in nodes[:-1])


def solve(
    n,
    nodes,
    edges,
    capacity,
    items,
    demand,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    node_to_idx = {j: i for i, j in enumerate(nodes)}

    precedence_edges = compute_precedence(nodes, items, demand)
    (
        predecessors,
        successors,
        transitive_precedence_edges,
    ) = compute_predecessors_and_successors(nodes, precedence_edges)
    not_inferred_precedence_edges = compute_not_inferred_precedence(
        predecessors, successors, precedence_edges
    )
    filtered_edges = {
        (i, j): w
        for (i, j), w in edges.items()
        if w >= 0
        and i != j
        and check_edge(i, j, nodes, not_inferred_precedence_edges, capacity)
        and (j, i) not in transitive_precedence_edges
        and (
            (i, j) not in transitive_precedence_edges
            or (i, j) in not_inferred_precedence_edges
        )
    }
    ub = compute_ub(nodes, filtered_edges)

    if ub == -1:
        print("The problem is infeasible")
        return

    edge_matrix = [
        [filtered_edges[i, j] if (i, j) in filtered_edges else ub + n for j in nodes]
        for i in nodes
    ]

    model = cp.CpoModel()

    x = cp.interval_var_list(n, end=(0, ub + n), length=1, name="x")
    pi = cp.sequence_var(x)

    distance = cp.transition_matrix(edge_matrix)
    model.add(cp.no_overlap(pi, distance, is_direct=True))

    for k in items:
        for i in nodes:
            if demand[i, k] > 0:
                p = node_to_idx[i]
            if demand[i, k] < 0:
                d = node_to_idx[i]

        model.add(cp.before(pi, x[p], x[d]))

    load = cp.step_at_start(x[0], capacity)

    for i in nodes[1:]:
        delta_q = sum(demand[i, k] for k in items)
        if delta_q > 0:
            load -= cp.step_at_start(x[node_to_idx[i]], delta_q)
        if delta_q < 0:
            load += cp.step_at_start(x[node_to_idx[i]], -delta_q)

    model.add(load >= 0)
    model.add(cp.first(pi, x[0]))
    model.add(cp.last(pi, x[-1]))

    model.add(cp.minimize(cp.start_of(x[-1]) - n + 1))

    if args.history is None:
        if verbose:
            result = model.solve(
                RelativeOptimalityTolerance=1e-5, TimeLimit=time_limit, Workers=threads
            )
        else:
            result = model.solve(
                RelativeOptimalityTolerance=1e-5,
                TimeLimit=time_limit,
                Workers=threads,
                LogVerbosity="Quiet",
            )
    else:
        if verbose:
            solver = cp.CpoSolver(
                model,
                RelativeOptimalityTolerance=1e-5,
                TimeLimit=time_limit,
                Workers=threads,
            )
        else:
            solver = cp.CpoSolver(
                model,
                RelativeOptimalityTolerance=1e-5,
                TimeLimit=time_limit,
                Workers=threads,
                LogVerbosity="Quiet",
            )

        with open(history, "w") as f:
            is_new_solution = True

            while is_new_solution:
                result = solver.search_next()
                is_new_solution = result.is_new_solution()

                if is_new_solution:
                    f.write(
                        "{}, {}\n".format(
                            time.perf_counter() - start, result.get_objective_value()
                        )
                    )

    if result.is_solution():
        solution = []
        time_with_nodes = []
        for i in nodes:
            v = result[x[node_to_idx[i]]]
            if len(v) > 0:
                time_with_nodes.append((v.start, i))
        for _, i in sorted(time_with_nodes):
            solution.append(i)

        print(result.get_objective_value())
        cost = round(result.get_objective_value())
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_tsplib.validate_mpdtsp(
            solution, cost, nodes, edges, capacity, items, demand
        )

        if validation_result:
            print("The solution is valid.")
            if result.is_solution_optimal():
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(result.get_objective_gap()))
                print("best bound: {}".format(result.get_objective_bound()))
        else:
            print("The solution is invalid.")
    elif result.get_solve_status() == "Infeasible":
        print("The problem is infeasible.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", "-t", type=int, default=1)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    n, nodes, edges, capacity, m, items, demand, _ = read_tsplib.read_mpdtsp(args.input)
    solve(
        n,
        nodes,
        edges,
        capacity,
        items,
        demand,
        time_limit=args.time_out,
        threads=args.threads,
        verbose=args.verbose,
        history=args.history,
    )
