#!/usr/bin/env python3

import argparse
import time

import gurobipy as gp
import read_tsptw

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


def solve_tsptw(
    n,
    nodes,
    edges,
    a,
    b,
    time_limit=None,
    threads=1,
    no_edge_reduction=False,
    time_window_reduction=False,
    mtz=False,
    history=None,
    makespan=False,
    mip_gap=1e-4,
):
    if time_window_reduction:
        a, b = read_tsptw.reduce_time_window(nodes, edges, a, b)

    if not no_edge_reduction:
        edges = read_tsptw.reduce_edges(nodes, edges, a, b)

    nodes_wo_0 = [i for i in nodes if i > 0]

    model = gp.Model()
    model.setParam("MipGap", mip_gap)
    model.setParam("Threads", threads)
    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)
    model.setParam("OutputFlag", 0)

    t = model.addVars(nodes_wo_0, vtype=gp.GRB.CONTINUOUS, lb=a, ub=b)

    if makespan:
        x = model.addVars(edges.keys(), vtype=gp.GRB.BINARY)
        t_n = model.addVar(vtype=gp.GRB.CONTINUOUS, obj=1)
    else:
        x = model.addVars(edges.keys(), vtype=gp.GRB.BINARY, obj=edges)
        t_n = model.addVar(vtype=gp.GRB.CONTINUOUS)

    model.addConstrs(t[i] - edges[0, i] * x[0, i] >= 0 for i in nodes_wo_0)
    model.addConstrs(
        t[i] - t[j] + (b[i] - a[j] + edges[i, j]) * x[i, j] <= b[i] - a[j]
        for (i, j) in edges
        if i > 0 and j > 0
    )
    model.addConstrs(
        gp.quicksum(x[i, j] for i in nodes if i != j and (i, j) in edges) == 1
        for j in nodes
    )
    model.addConstrs(
        gp.quicksum(x[i, j] for j in nodes if j != i and (i, j) in edges) == 1
        for i in nodes
    )
    model.addConstrs(t[i] + edges[i, 0] <= t_n for i in nodes_wo_0)

    if any(c == 0 for c in edges.values()):
        if mtz:
            add_mtz(n, nodes, edges, x, model)
        else:
            add_flow_based(n, nodes, edges, x, model)

    if history is None:
        model.optimize()
    else:
        with open(history, "w") as f:
            callback = get_callback(f)
            model.optimize(callback)

    status = model.getAttr("Status")
    sol_count = model.getAttr("SolCount")

    if status == gp.GRB.INFEASIBLE:
        print("The problem is infeasible.")
    elif sol_count > 0:
        tour = [0]
        i = 0
        while True:
            for j in nodes:
                if i == j:
                    continue
                if (i, j) in edges and x[i, j].x > 0.5:
                    tour.append(j)
                    i = j
                    break
            if j == 0:
                break
        print(tour)
        cost = model.objVal
        print("cost: {}".format(cost))

        validation_result = read_tsptw.validate(
            n, edges, a, b, tour, cost, makespan=makespan
        )

        print("Search time: {}s".format(model.getAttr("Runtime")))

        if validation_result:
            print("The solution is valid.")
            if status == gp.GRB.OPTIMAL:
                print("optimal cost: {}".format(model.objVal))
            else:
                print("gap: {}".format(model.getAttr("MIPGap")))
                print("best bound: {}".format(model.getAttr("ObjBound")))
        else:
            print("The solution is invalid.")


def add_mtz(n, nodes, x, model):
    nodes_wo_0 = [i for i in nodes if i > 0]
    w = model.addVars(nodes_wo_0, vtype=gp.GRB.CONTINUOUS)
    model.addConstrs(
        w[i] - w[j] + (n - 1) * x[i, j] <= n - 2
        for i in nodes_wo_0
        for j in nodes_wo_0
        if i != j
    )
    return w


def add_flow_based(n, nodes, edges, x, model):
    nodes_wo_0 = [i for i in nodes if i > 0]
    y = model.addVars(edges.keys(), vtype=gp.GRB.CONTINUOUS, lb=0)
    model.addConstrs(y[i, j] <= (n - 1) * x[i, j] for (i, j) in edges)
    model.addConstr(gp.quicksum(y[0, j] for j in nodes_wo_0) == n - 1)
    model.addConstrs(
        gp.quicksum(y[i, j] for i in nodes if i != j and (i, j) in edges)
        - gp.quicksum(y[j, k] for k in nodes if k != j and (j, k) in edges)
        == 1
        for j in nodes_wo_0
    )
    return y


def reduce_edges(nodes, edges, a, b):
    print("edges: {}".format(len(edges)))
    forward_dependent = []
    for i, j in edges.keys():
        if i == 0 or j == 0 or a[i] <= b[j]:
            forward_dependent.append((i, j))

    direct_forward_dependent = {}
    for i, j in forward_dependent:
        if (
            i == 0
            or j == 0
            or all(b[i] > a[k] or b[k] > a[j] for k in nodes if k != 0)
            or (a[i] == a[j] and b[i] == b[j])
        ):
            direct_forward_dependent[i, j] = edges[i, j]

    print("reduced edges: {}".format(len(direct_forward_dependent)))
    return direct_forward_dependent


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", "-t", type=int, default=1)
    parser.add_argument("--no-edge-reduction", "-n", action="store_true")
    parser.add_argument("--time-window-reduction", "-w", action="store_true")
    parser.add_argument("--mtz", "-m", action="store_true")
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    parser.add_argument("--makespan", action="store_true")
    parser.add_argument("--mip-gap", default=1e-4, type=float)
    args = parser.parse_args()

    n, nodes, edges, a, b = read_tsptw.read(args.input)
    solve_tsptw(
        n,
        nodes,
        edges,
        a,
        b,
        time_limit=args.time_out,
        threads=args.threads,
        no_edge_reduction=args.no_edge_reduction,
        time_window_reduction=args.time_window_reduction,
        mtz=args.mtz,
        history=args.history,
        makespan=args.makespan,
        mip_gap=args.mip_gap,
    )
