#!/usr/bin/env python3

import argparse
import re
import math
import os
import time

import gurobipy as gp

import read_tsplib


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


def solve_asymmetric(
    n,
    nodes,
    edges,
    capacity,
    demand,
    depot,
    routes=None,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    model = gp.Model()
    model.setParam("Threads", threads)
    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)
    if not verbose:
        model.setParam("OutputFlag", 0)
    x = model.addVars(edges, vtype=gp.GRB.BINARY, obj=edges)
    f = model.addVars(edges, vtype=gp.GRB.CONTINUOUS)
    model.addConstrs(f[depot, j] == 0 for j in nodes if j != depot)
    model.addConstrs(
        gp.quicksum(x[i, j] for j in nodes if (i, j) in edges) == 1
        for i in nodes
        if i != depot
    )
    model.addConstrs(
        gp.quicksum(x[j, i] for j in nodes if (j, i) in edges) == 1
        for i in nodes
        if i != depot
    )
    if routes is None:
        model.addConstr(gp.quicksum(x[1, i] for i in nodes if (1, i) in edges) <= n - 1)
        model.addConstr(gp.quicksum(x[i, 1] for i in nodes if (i, 1) in edges) <= n - 1)
    else:
        model.addConstr(
            gp.quicksum(x[1, i] for i in nodes if (1, i) in edges) == routes
        )
        model.addConstr(
            gp.quicksum(x[i, 1] for i in nodes if (i, 1) in edges) == routes
        )
    model.addConstrs(
        gp.quicksum(f[i, j] for j in nodes if (i, j) in edges)
        == gp.quicksum(f[j, i] for j in nodes if (j, i) in edges) + demand[i]
        for i in nodes
        if i != depot
    )
    model.addConstrs(f[i, j] >= demand[i] * x[i, j] for (i, j) in edges)
    model.addConstrs(f[i, j] <= (capacity - demand[j]) * x[i, j] for (i, j) in edges)
    model.optimize()

    if history is None:
        model.optimize()
    else:
        with open(history, "w") as f:
            callback = get_callback(f)
            model.optimize(callback)

    status = model.getAttr("Status")
    sol_count = model.getAttr("SolCount")

    if status == gp.GRB.INFEASIBLE:
        print("infeasible")
    elif sol_count > 0:
        for i in nodes:
            if (depot, i) in edges and x[depot, i].X > 0.5:
                text = str(depot)
                current = i
                while current != depot:
                    text += " -> {}".format(current)
                    for j in nodes:
                        if (current, j) in edges and x[current, j].X > 0.5:
                            current = j
                            break
                text += " -> {}".format(depot)
                print(text)
        print("cost: {}".format(model.objVal))

        if status == gp.GRB.OPTIMAL:
            print("optimal cost: {}".format(model.objVal))
        else:
            print("gap: {}".format(model.getAttr("MIPGap")))
            print("best bound: {}".format(model.getAttr("ObjBound")))


def solve_symmetric(
    n,
    nodes,
    edges,
    capacity,
    demand,
    depot,
    routes=None,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    model = gp.Model()
    model.setParam("Threads", threads)
    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)
    if not verbose:
        model.setParam("OutputFlag", 0)
    nodes_wo_depot = [i for i in nodes if i != depot]
    edges_wo_depot = {
        (i, j): w for (i, j), w in edges.items() if i != depot and j != depot
    }
    x0_ub = {j: 2 for j in nodes_wo_depot}
    if routes is None:
        for j in nodes_wo_depot:
            if sum(demand[i] for i in nodes_wo_depot if i != j) > (n - 2) * capacity:
                x0_ub[j] = 1
    else:
        for j in nodes_wo_depot:
            if (
                sum(demand[i] for i in nodes_wo_depot if i != j)
                > (routes - 1) * capacity
            ):
                x0_ub[j] = 1
    x0_obj = {j: edges[depot, j] for j in nodes_wo_depot}
    x0 = model.addVars(nodes_wo_depot, vtype=gp.GRB.INTEGER, lb=0, ub=x0_ub, obj=x0_obj)
    x = model.addVars(edges_wo_depot, vtype=gp.GRB.BINARY, obj=edges_wo_depot)
    edges_for_f = {(i, j): w for (i, j), w in edges.items() if j != depot}
    f = model.addVars(edges_for_f, vtype=gp.GRB.CONTINUOUS)
    model.addConstrs(f[depot, j] == 0 for j in nodes if j != depot)
    u_lb = {i: i - 1 for i in nodes_wo_depot if i != n}
    u = model.addVars(
        [i for i in nodes_wo_depot if i != n], vtype=gp.GRB.CONTINUOUS, lb=u_lb
    )
    p = model.addVars(nodes_wo_depot, vtype=gp.GRB.BINARY)
    t = model.addVars(nodes_wo_depot, vtype=gp.GRB.CONTINUOUS)
    model.addConstrs(
        gp.quicksum(x[i, j] for j in nodes if (i, j) in edges_wo_depot) + p[i] == 1
        for i in nodes_wo_depot
    )
    model.addConstrs(
        gp.quicksum(x[j, i] for j in nodes if (j, i) in edges_wo_depot) + x0[i] - p[i]
        == 1
        for i in nodes_wo_depot
    )
    model.addConstrs(
        t[i] + gp.quicksum(f[i, j] for j in nodes if (i, j) in edges_for_f)
        == gp.quicksum(f[j, i] for j in nodes if (j, i) in edges_for_f) + demand[i]
        for i in nodes_wo_depot
    )
    model.addConstrs(f[i, j] >= demand[i] * x[i, j] for (i, j) in edges_wo_depot)
    model.addConstrs(
        f[i, j] <= (capacity - demand[j]) * x[i, j] for (i, j) in edges_wo_depot
    )
    model.addConstrs(t[i] >= demand[i] * p[i] for i in nodes_wo_depot)
    model.addConstrs(t[i] <= capacity * p[i] for i in nodes_wo_depot)
    if routes is None:
        model.addConstr(gp.quicksum(x0[i] for i in nodes_wo_depot) <= 2 * (n - 1))
        model.addConstr(gp.quicksum(p[i] for i in nodes_wo_depot) <= n - 1)
    else:
        model.addConstr(gp.quicksum(x0[i] for i in nodes_wo_depot) == 2 * routes)
        model.addConstr(gp.quicksum(p[i] for i in nodes_wo_depot) == routes)
    model.addConstrs(
        u[i] <= (i - 1) * p[i] + (n - 2) * (1 - p[i]) for i in nodes_wo_depot if i != n
    )
    model.addConstrs(
        u[i] - u[j] + (n - j - 1) * x[i, j] + (n - max(i, j) - 1) * x[j, i] <= n - j - 1
        for (i, j) in edges_wo_depot
        if i != n and j != n
    )
    model.addConstrs(
        gp.quicksum(p[i] for i in nodes_wo_depot if i >= j)
        >= math.ceil(sum(demand[i] for i in nodes_wo_depot if i >= j) / capacity)
        for j in nodes_wo_depot
    )

    if history is None:
        model.optimize()
    else:
        with open(history, "w") as f:
            callback = get_callback(f)
            model.optimize(callback)

    status = model.getAttr("Status")
    sol_count = model.getAttr("SolCount")

    if status == gp.GRB.INFEASIBLE:
        print("infeasible")
    elif sol_count > 0:
        cost = round(model.objVal)
        end_to_subtour = {}
        solution = [depot]
        for i in nodes_wo_depot:
            if (depot, i) in edges and x0[i].X > 0.5:
                subtour = [depot]
                current = i
                next = True
                while next:
                    subtour.append(current)
                    next = False
                    for j in nodes:
                        if (current, j) in edges_wo_depot and x[current, j].X > 0.5:
                            current = j
                            next = True
                            break
                if subtour[-1] in end_to_subtour:
                    solution += subtour[1:-1] + list(
                        reversed(end_to_subtour[subtour[-1]])
                    )
                    del end_to_subtour[subtour[-1]]
                else:
                    end_to_subtour[subtour[-1]] = subtour

        for subtour in end_to_subtour.values():
            solution += subtour[1:] + [depot]

        print(solution)
        validation_result = read_tsplib.validate_cvrp(
            n, nodes, edges, capacity, demand, depot, solution, cost, k=routes
        )
        if validation_result:
            print("The solution is valid.")
            print("cost: {}".format(cost))

            if status == gp.GRB.OPTIMAL:
                print("optimal cost: {}".format(model.objVal))
            else:
                print("gap: {}".format(model.getAttr("MIPGap")))
                print("bound: {}".format(model.getAttr("ObjBound")))
        else:
            print("The solution is invalid.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", "-t", type=int, default=1)
    parser.add_argument("--asymmetric", "-a", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--not-fix-route", "-n", action="store_true")
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    if args.not_fix_route:
        k = None
    else:
        name = os.path.basename(args.input)
        m = re.match(r".+k(\d+).+", name)
        k = int(m.group(1))

    n, nodes, edges, capacity, demand, depot, symmetric = read_tsplib.read_cvrp(
        args.input
    )
    if symmetric and not args.asymmetric:
        solve_symmetric(
            n,
            nodes,
            edges,
            capacity,
            demand,
            depot,
            routes=k,
            time_limit=args.time_out,
            threads=args.threads,
            verbose=args.verbose,
            history=args.history,
        )
    else:
        solve_asymmetric(
            n,
            nodes,
            edges,
            capacity,
            demand,
            depot,
            routes=k,
            time_limit=args.time_out,
            threads=args.threads,
            verbose=args.verbose,
            history=args.history,
        )
