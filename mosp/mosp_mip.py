#!/usr/bin/env python3

import argparse
import time

import gurobipy as gp
import read_mosp

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


def solve(item_to_patterns, pattern_to_items, time_limit=None, threads=1, history=None, memory_limit=None):
    item_to_neighbors = read_mosp.compute_item_to_neighbors(
        item_to_patterns, pattern_to_items
    )

    m = len(item_to_patterns)
    items = list(range(m))
    lb = min(len(item_to_neighbors[i]) for i in items)
    t_bar = m - (lb - 1)
    times = list(range(t_bar))

    model = gp.Model()

    model.setParam("Threads", threads)

    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)

    if memory_limit is not None:
        model.params.SoftMemLimit = memory_limit

    model.setParam("OutputFlag", 0)

    x = model.addVars(items, times, vtype=gp.GRB.BINARY)
    w = model.addVars(items, times, vtype=gp.GRB.BINARY)
    c = model.addVar(vtype=gp.GRB.INTEGER, lb=0, obj=1)
    model.addConstrs(gp.quicksum(x[i, t] for i in items) == 1 for t in times[:-1])
    model.addConstr(gp.quicksum(x[i, t_bar - 1] for i in items) == lb)
    model.addConstrs(gp.quicksum(x[i, t] for t in times) == 1 for i in items)
    model.addConstrs(
        gp.quicksum(x[k, t_p] for k in item_to_neighbors[i] for t_p in range(t + 1))
        <= min(t + 1, len(item_to_neighbors[i])) * w[i, t]
        for i in items
        for t in times[:-1]
    )
    model.addConstrs(c >= gp.quicksum(w[i, t] for i in items) - t for t in times)
    model.addConstrs(w[i, t_bar - 1] == 1 for i in items)

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
        item_order = []
        for t in times:
            for i in items:
                if x[i, t].X > 0.5:
                    item_order.append(i)

        solution = read_mosp.item_order_to_pattern_order(item_to_patterns, item_order)
        cost = round(model.objVal)
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_mosp.validate(
            item_to_patterns, pattern_to_items, solution, cost
        )

        if validation_result:
            print("The solution is valid.")
            if status == gp.GRB.OPTIMAL:
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(model.getAttr("MIPGap")))
                print("best bound: {}".format(model.getAttr("ObjBound")))
        else:
            # It is possible that the objective cost does not match the actual cost
            # as the constraints are inequalities.
            print("The solution is invalid.")
            print("gap: {}".format(model.getAttr("MIPGap")))
            print("best bound: {}".format(model.getAttr("ObjBound")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    parser.add_argument("--memory-out", type=float)
    args = parser.parse_args()

    item_to_patterns, pattern_to_items = read_mosp.read(args.input)
    solve(
        item_to_patterns,
        pattern_to_items,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
        memory_limit=args.memory_out,
    )
