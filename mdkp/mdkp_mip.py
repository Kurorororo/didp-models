#!/usr/bin/env python3

import argparse
import time

import gurobipy as gp
import read_mdkp

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
    m,
    profit,
    weight,
    capacity,
    time_limit=None,
    threads=1,
    history=None,
):
    model = gp.Model()

    x = model.addVars(n, vtype=gp.GRB.BINARY, obj=profit)

    model.addConstrs(
        gp.quicksum(weight[i][j] * x[j] for j in range(n)) <= capacity[i]
        for i in range(m)
    )

    model.modelSense = gp.GRB.MAXIMIZE

    model.setParam("Threads", threads)

    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)

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
        solution = [j for j in range(n) if x[j].x > 0.5]
        print(solution)
        cost = int(round(model.objVal))
        print("cost: {}".format(cost))

        validation_result = read_mdkp.validate_mdkp(
            m, profit, weight, capacity, solution, cost
        )

        print("Search time: {}s".format(model.getAttr("Runtime")))

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
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    n, m, profit, weight, capacity = read_mdkp.read_mdkp(args.input)

    solve(
        n,
        m,
        profit,
        weight,
        capacity,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
    )
