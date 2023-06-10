#!/usr/bin/env python3

import argparse
from collections import deque
import time

import gurobipy as gp

import read_tsplib
from mpdtsp_util import (
    compute_precedence,
    compute_predecessors_and_successors,
    check_edge,
    compute_not_inferred_precedence,
)


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


def check_flow(
    i,
    j,
    p,
    q,
    predecessors,
    successors,
    not_inferred_precedence_edges,
):
    if (
        i in predecessors[p] | successors[q]
        or i == q
        or j in predecessors[p] | successors[q]
        or j == p
    ):
        return False

    return (
        i in (p, q)
        or i in (predecessors[p] | predecessors[q] | successors[p] | successors[q])
        or j in (p, q)
        or j in (predecessors[p] | predecessors[q] | successors[p] | successors[q])
        or (
            (
                sum(
                    not_inferred_precedence_edges[r, s]
                    for r in nodes
                    for s in (i, j)
                    if (r, s) in not_inferred_precedence_edges and r not in (i, j)
                )
                + not_inferred_precedence_edges[p, q]
                <= capacity
            )
            and (
                sum(
                    not_inferred_precedence_edges[b]
                    for b in (
                        {
                            (i, k)
                            for k in nodes
                            if (i, k) in not_inferred_precedence_edges
                        }
                        | {
                            (k, j)
                            for k in nodes
                            if (k, j) in not_inferred_precedence_edges
                        }
                    )
                )
                + not_inferred_precedence_edges[p, q]
                <= capacity
            )
            and (
                sum(
                    not_inferred_precedence_edges[r, s]
                    for r in (i, j)
                    for s in nodes
                    if (r, s) in not_inferred_precedence_edges and s not in (i, j)
                )
                + not_inferred_precedence_edges[p, q]
                <= capacity
            )
        )
    )


def compute_dipaths(nodes, not_inferred_precedence_edges):
    open_list = deque([(nodes[0], None)])
    closed_list = set()
    paths = {}

    while len(open_list) > 0:
        i, parent = open_list[0]
        open_list.popleft()
        if i not in closed_list:
            closed_list.add(i)
            if parent is None:
                paths[i] = []
            else:
                paths[i] = list(paths[parent]) + [(parent, i)]
            for j in nodes:
                if (i, j) in not_inferred_precedence_edges and j not in closed_list:
                    open_list.append((j, i))

    return paths


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
        and check_edge(i, j, nodes, not_inferred_precedence_edges, capacity)
        and (j, i) not in transitive_precedence_edges
        and (
            (i, j) not in transitive_precedence_edges
            or (i, j) in not_inferred_precedence_edges
        )
    }
    total_demand = {i: sum(demand[i, j] for j in items) for i in nodes}
    paths = compute_dipaths(nodes, not_inferred_precedence_edges)

    model = gp.Model()

    x = model.addVars(filtered_edges.keys(), vtype=gp.GRB.BINARY, obj=edges)
    f = model.addVars(
        not_inferred_precedence_edges.keys(),
        filtered_edges.keys(),
        vtype=gp.GRB.BINARY,
    )

    model.addConstrs(
        gp.quicksum(x[i, j] for j in nodes if (i, j) in filtered_edges) == 1
        for i in nodes[:-1]
    )
    model.addConstrs(
        gp.quicksum(x[j, i] for j in nodes if (j, i) in filtered_edges) == 1
        for i in nodes[1:]
    )

    # flow constraints
    model.addConstrs(
        gp.quicksum(f[(p, q, i, j)] for j in nodes if (i, j) in filtered_edges)
        - gp.quicksum(f[(p, q, j, i)] for j in nodes if (j, i) in filtered_edges)
        == (1 if i == p else -1 if i == q else 0)
        for i in nodes
        for (p, q) in not_inferred_precedence_edges
    )
    model.addConstrs(
        f[(*b, *a)] <= x[a]
        for a in filtered_edges
        for b in not_inferred_precedence_edges
    )

    # capacity constraints
    model.addConstrs(
        gp.quicksum(d * f[(*b, i, j)] for b, d in not_inferred_precedence_edges.items())
        <= (capacity - max(0, -total_demand[i], total_demand[j])) * x[i, j]
        for (i, j) in filtered_edges
    )

    # filter flow variables
    model.addConstrs(
        f[p, q, i, j] == 0
        for (i, j) in filtered_edges
        for (p, q) in not_inferred_precedence_edges
        if not check_flow(
            i,
            j,
            p,
            q,
            predecessors,
            successors,
            not_inferred_precedence_edges,
        )
    )

    # incomparable pair (IP) equation
    model.addConstrs(
        gp.quicksum(
            f[(*b, i, k)]
            for b in paths[j]
            for k in nodes
            if k != i and (i, k) in filtered_edges
        )
        + gp.quicksum(
            f[(*b, k, j)]
            for b in paths[i]
            for k in nodes
            if k != j and (k, j) in filtered_edges
        )
        == 1
        for i in nodes[1:-1]
        for j in nodes[1:-1]
        if i != j and i not in successors[j] and j not in successors[i]
    )

    model.setParam("Threads", threads)

    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)

    if not verbose:
        model.setParam("OutputFlag", 0)

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
        i = nodes[0]
        tour = [i]
        while True:
            for j in nodes:
                if i == j:
                    continue
                if (i, j) in filtered_edges and x[i, j].x > 0.5:
                    tour.append(j)
                    i = j
                    break
            if j == nodes[-1]:
                break
        print(tour)
        cost = round(model.objVal)
        print("cost: {}".format(cost))

        validation_result = read_tsplib.validate_mpdtsp(
            tour, cost, nodes, edges, capacity, items, demand
        )

        if validation_result:
            print("The solution is valid.")
            if status == gp.GRB.OPTIMAL:
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(model.getAttr("MIPGap")))
                print("best bound: {}".format(model.getAttr("ObjBound")))
        else:
            print("The solution is invalid.")


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
