#!/usr/bin/env python3

import argparse
import time

import gurobipy as gp
import read_graph_clear

start = time.perf_counter()


def get_callback(file):
    def dump_solution(model, where):
        if where == gp.GRB.Callback.MIPSOL:
            file.write(
                "{}, {}\n".format(
                    time.perf_counter() - start,
                    model.cbGet(gp.GRB.Callback.MIPSOL_OBJ),
                )
            )

    return dump_solution


def solve(
    n,
    node_weights,
    edge_weights,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    nodes = list(range(n))
    z_lb = 1
    z_ub = max(node_weights) + sum(edge_weights.values())

    model = gp.Model()
    model.setParam("Threads", threads)
    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)
    model.setParam("Symmetry", 2)
    if not verbose:
        model.setParam("OutputFlag", 0)

    x = model.addVars(nodes, nodes, vtype=gp.GRB.BINARY)
    y = model.addVars(edge_weights, nodes, vtype=gp.GRB.BINARY)
    z = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=z_lb, ub=z_ub, obj=1)

    model.addConstr(
        z
        >= gp.quicksum(node_weights[i] * x[i, 0] for i in nodes)
        + gp.quicksum(b * y[i, j, 0] for (i, j), b in edge_weights.items())
    )
    model.addConstrs(
        z
        >= gp.quicksum(node_weights[i] * (x[i, t] - x[i, t - 1]) for i in nodes)
        + gp.quicksum(b * y[i, j, t] for (i, j), b in edge_weights.items())
        for t in range(1, n)
    )
    model.addConstrs(gp.quicksum(x[i, t] for i in nodes) == t + 1 for t in nodes)
    model.addConstrs(x[i, t] <= x[i, t + 1] for i in nodes for t in range(n - 1))
    model.addConstrs(
        x[i, t] - x[j, t] <= y[i, j, t] for (i, j) in edge_weights for t in nodes
    )
    model.addConstrs(
        x[j, t] - x[i, t] <= y[i, j, t] for (i, j) in edge_weights for t in nodes
    )
    model.addConstrs(
        x[i, t] - x[i, t - 1] <= y[i, j, t]
        for (i, j) in edge_weights
        for t in range(1, n)
    )
    model.addConstrs(
        x[j, t] - x[j, t - 1] <= y[i, j, t]
        for (i, j) in edge_weights
        for t in range(1, n)
    )

    if history is None:
        model.optimize()
    else:
        with open(history, "w") as f:
            callback = get_callback(f)
            model.optimize(callback)

    status = model.getAttr("Status")
    sol_count = model.getAttr("SolCount")
    print("Search time: {}s".format(model.getAttr("Runtime")))

    if status == gp.GRB.INFEASIBLE:
        print("infeasible")
    elif sol_count > 0:
        clean = set()
        solution = []
        for t in nodes:
            for i in nodes:
                if i not in clean and x[i, t].X > 0.5:
                    delta_c = set(
                        (u, v)
                        for (u, v) in edge_weights
                        if (u in clean and v not in clean)
                        or (u not in clean and v in clean)
                    )
                    delta_sigma = set(
                        (u, v) for (u, v) in edge_weights if u == i or v == i
                    )
                    delta = delta_c.union(delta_sigma)
                    robots = node_weights[i] + sum(
                        edge_weights[u, v] for (u, v) in delta
                    )
                    print("sweep {}, robots: {}".format(i, robots))
                    clean.add(i)
                    solution.append(i)
                    continue

        cost = round(model.objVal)
        print(solution)
        print("cost: {}".format(cost))
        best_bound = model.getAttr("ObjBound")
        gap = model.getAttr("MIPGap")

        validation_result = read_graph_clear.validate(
            n, node_weights, edge_weights, solution, cost
        )

        if validation_result:
            print("The solution is valid.")
            if status == gp.GRB.OPTIMAL:
                print("optimal cost: {}".format(model.objVal))
            else:
                print("gap: {}".format(model.getAttr("MIPGap")))
                print("best bound: {}".format(model.getAttr("ObjBound")))
        else:
            # It is possible that the objective cost does not match the actual cost
            # as the constraints are inequalities.
            print("The solution is invalid.")
            print("gap: {}".format(gap))
            print("best bound: {}".format(best_bound))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", "-t", type=int, default=1)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    n, node_weights, edge_weights = read_graph_clear.read(args.input)
    solve(
        n,
        node_weights,
        edge_weights,
        time_limit=args.time_out,
        threads=args.threads,
        verbose=args.verbose,
        history=args.history,
    )
