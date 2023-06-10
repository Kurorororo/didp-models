#!/usr/bin/env python3

import argparse
import time

import gurobipy as gp

import read_bpp


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


def solve(n, c, weights, time_limit=None, threads=1, history=None):
    ub, weights = read_bpp.first_fit_decreasing(c, weights)
    items = list(range(n))
    bins = list(range(ub))
    bin_item_pairs = {(i, j) for i in bins for j in items if i <= j}

    model = gp.Model()
    model.setParam("Threads", threads)
    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)
    model.setParam("OutputFlag", 0)
    x = model.addVars(bin_item_pairs, vtype=gp.GRB.BINARY)
    y = model.addVars(bins, vtype=gp.GRB.BINARY, obj=1)
    model.addConstrs(
        gp.quicksum(weights[j] * x[i, j] for j in items if (i, j) in bin_item_pairs)
        <= c * y[i]
        for i in bins
    )
    model.addConstrs(
        gp.quicksum(x[i, j] for i in bins if (i, j) in bin_item_pairs) == 1
        for j in items
    )
    model.addConstrs(y[i] >= y[i + 1] for i in bins if i < ub - 1)
    model.addConstrs(x[i, j] <= y[i] for (i, j) in bin_item_pairs)

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
        solution = []
        for i in bins:
            items_in_bin = []
            for j in items:
                if (i, j) in bin_item_pairs and x[i, j].X > 0.5:
                    items_in_bin.append(j)
            if len(items_in_bin) > 0:
                solution.append(items_in_bin)
        print(solution)
        print("cost: {}".format(cost))
        validation_result = read_bpp.validate(n, c, weights, solution, cost)
        if validation_result:
            print("The solution is valid.")

            if status == gp.GRB.OPTIMAL:
                print("optimal cost: {}".format(model.objVal))
            else:
                print("gap: {}".format(model.getAttr("MIPGap")))
                print("best bound: {}".format(model.getAttr("ObjBound")))
        else:
            print("The solution is invalid.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    n, c, weights = read_bpp.read(args.input)
    solve(
        n,
        c,
        weights,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
    )
