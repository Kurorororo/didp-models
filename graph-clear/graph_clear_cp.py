#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp

import read_graph_clear


start = time.perf_counter()


def solve_n(n, node_weights, edge_weights, time_limit=None, threads=1, history=None):
    nodes = list(range(n))
    edge_to_id = {}
    edges = []
    m = 0
    for i in nodes:
        for j in nodes:
            if (i, j) in edge_weights:
                edge_to_id[i, j] = m
                edges.append((i, j))
                m += 1
    z_lb = 1
    c_block = sum(edge_weights.values())
    z_ub = max(node_weights) + c_block
    c_sweep = max(
        node_weights[i]
        + sum(
            (edge_weights[i, j] if (i, j) in edge_weights else 0)
            + (edge_weights[j, i] if (j, i) in edge_weights else 0)
            for j in nodes
        )
        for i in nodes
    )

    model = cp.CpoModel()
    var_t = cp.integer_var_list(n, min=0, max=n - 1)
    var_l = cp.integer_var_list(m, min=0, max=n - 1)
    var_u = cp.integer_var_list(m, min=0, max=n - 1)
    var_s = cp.integer_var_list(n, min=1, max=c_sweep)
    var_b = cp.integer_var_list(n, min=0, max=c_block)
    var_i = [cp.integer_var_list(n, min=0, max=1) for _ in range(m)]
    var_z = cp.integer_var(min=z_lb, max=z_ub)

    model.add(cp.minimize(var_z))

    model.add(var_z == cp.max(var_s[t] + var_b[t] for t in nodes))

    for i in nodes:
        for t in nodes:
            model.add(
                cp.if_then(
                    var_t[i] == t,
                    var_s[t]
                    == node_weights[i]
                    + sum(
                        (edge_weights[i, j] if (i, j) in edge_weights else 0)
                        + (edge_weights[j, i] if (j, i) in edge_weights else 0)
                        for j in nodes
                    ),
                )
            )

    model.add(cp.all_diff(var_t))

    for i, j in edges:
        e = edge_to_id[i, j]
        model.add(cp.if_then(var_t[i] < var_t[j], var_l[e] == var_t[i]))
        model.add(cp.if_then(var_t[j] < var_t[i], var_l[e] == var_t[j]))
        model.add(cp.if_then(var_t[i] < var_t[j], var_u[e] == var_t[j]))
        model.add(cp.if_then(var_t[j] < var_t[i], var_u[e] == var_t[i]))

        for t in nodes:
            model.add(
                cp.if_then(
                    cp.logical_and(
                        cp.logical_and(var_l[e] <= t, var_u[e] >= t),
                        cp.logical_and(var_t[i] != t, var_t[j] != t),
                    ),
                    var_i[e][t] == 1,
                )
            )
    for t in nodes:
        model.add(
            var_b[t]
            == cp.sum(
                edge_weights[i, j] * var_i[edge_to_id[i, j]][t] for (i, j) in edges
            )
        )

    phase = cp.search_phase(
        vars=var_t,
        varchooser=cp.select_smallest(cp.domain_size()),
        valuechooser=cp.select_smallest(cp.value()),
    )
    model.set_search_phases(phase)

    if args.history is None:
        result = model.solve(
            TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
        )
    else:
        solver = cp.CpoSolver(
            model, TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
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
        for t in range(n):
            for i in range(n):
                if result[var_t[i]] == t:
                    solution.append(i)

        cost = round(result.get_objective_value())
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_graph_clear.validate(
            n, node_weights, edge_weights, solution, cost
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


def solve_s(n, node_weights, edge_weights, time_limit=None, threads=1, history=None):
    nodes = list(range(n))
    z_lb = 1
    z_ub = max(node_weights) + sum(edge_weights.values())

    flatten_edge_weights = []
    for i in nodes:
        for j in nodes:
            if (i, j) in edge_weights:
                flatten_edge_weights.append(edge_weights[i, j])
            elif (j, i) in edge_weights:
                flatten_edge_weights.append(edge_weights[j, i])
            else:
                flatten_edge_weights.append(0)

    model = cp.CpoModel()
    z = cp.integer_var(min=z_lb, max=z_ub)
    w = cp.integer_var_list(n, min=0, max=n - 1)
    model.add(cp.all_diff(w))
    model.add(cp.minimize(z))
    for t in nodes:
        rhs = cp.element(node_weights, w[t])
        for i in nodes:
            rhs += cp.element(flatten_edge_weights, w[t] * n + i)
        for i in range(t):
            for j in range(n):
                rhs += cp.element(flatten_edge_weights, w[i] * n + j)
        for i in range(t):
            for j in range(t):
                rhs -= cp.element(flatten_edge_weights, w[i] * n + w[j])
        for i in range(t):
            rhs -= cp.element(flatten_edge_weights, w[i] * n + w[t])

        model.add(z >= rhs)

    phase = cp.search_phase(
        vars=w,
        varchooser=cp.select_smallest(cp.domain_size()),
        valuechooser=cp.select_smallest(cp.value_impact()),
    )
    model.set_search_phases(phase)

    if args.history is None:
        result = model.solve(
            TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
        )
    else:
        solver = cp.CpoSolver(
            model, TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
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
        for t in range(n):
            solution.append(result[w[t]])

        cost = round(result.get_objective_value())
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_graph_clear.validate(
            n, node_weights, edge_weights, solution, cost
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
    elif result.get_solve_status() == "infeasible":
        print("The problem is infeasible.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", "-t", type=int, default=1)
    parser.add_argument("--use-s", "-s", action="store_true")
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    n, node_weights, edge_weights = read_graph_clear.read(args.input)
    if args.use_s:
        solve_s(
            n,
            node_weights,
            edge_weights,
            time_limit=args.time_out,
            threads=args.threads,
            history=args.history,
        )
    else:
        solve_n(
            n,
            node_weights,
            edge_weights,
            time_limit=args.time_out,
            threads=args.threads,
            history=args.history,
        )
