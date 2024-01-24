#!/usr/bin/env python3

import argparse
import time

import gurobipy as gp
import read_optw

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
    vertices,
    service_time,
    profit,
    opening,
    closing,
    distance,
    time_limit=None,
    threads=1,
    history=None,
):
    model = gp.Model()

    last = len(vertices)
    extended_vertices = vertices + [last]
    extended_opening = opening + [opening[0]]
    extended_closing = closing + [closing[0]]
    extended_distance = [
        [service_time[i] + distance[i][j] for j in vertices]
        + [service_time[i] + distance[i][0]]
        for i in vertices
    ] + [[service_time[0] + distance[0][j] for j in vertices] + [0]]
    objective_coefficient = {
        (i, j): profit[i] if 0 < i < last else 0
        for i in extended_vertices[:-1]
        for j in extended_vertices[1:]
    }

    x = model.addVars(
        extended_vertices[:-1],
        extended_vertices[1:],
        vtype=gp.GRB.BINARY,
        obj=objective_coefficient,
    )
    s = model.addVars(
        extended_vertices,
        vtype=gp.GRB.CONTINUOUS,
        lb=extended_opening,
        ub=extended_closing,
    )

    model.addConstr(gp.quicksum(x[0, j] for j in extended_vertices[1:]) == 1)
    model.addConstr(gp.quicksum(x[i, last] for i in extended_vertices[:-1]) == 1)

    model.addConstrs(
        gp.quicksum(x[i, k] for i in extended_vertices[:-1])
        == gp.quicksum(x[k, j] for j in extended_vertices[1:])
        for k in extended_vertices[1:-1]
    )
    model.addConstrs(
        gp.quicksum(x[i, k] for i in extended_vertices[:-1]) <= 1
        for k in extended_vertices[1:-1]
    )
    model.addConstrs(
        gp.quicksum(x[k, j] for j in extended_vertices[1:]) <= 1
        for k in extended_vertices[1:-1]
    )

    model.addConstrs(
        s[i] + extended_distance[i][j] - s[j]
        <= (extended_closing[i] + extended_distance[i][j] - extended_opening[j])
        * (1 - x[i, j])
        for i in extended_vertices[:-1]
        for j in extended_vertices[1:]
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
        tour = [0]
        i = 0
        while True:
            for j in extended_vertices[1:]:
                if i == j:
                    continue
                if x[i, j].x > 0.5:
                    if j < last:
                        tour.append(j)
                        i = j
                    break
            if j == last:
                tour.append(0)
                break
        print(tour)
        cost = model.objVal
        print("cost: {}".format(cost))

        validation_result = read_optw.validate_optw(
            service_time, profit, opening, closing, distance, tour, cost
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--history", type=str)
    parser.add_argument("--round-to-second", action="store_true")
    args = parser.parse_args()

    vertices, service_time, profit, opening, closing, distance = read_optw.read_optw(
        args.input
    )

    if args.round_to_second:
        service_time, opening, closing, distance = read_optw.round_to_second(
            service_time, opening, closing, distance
        )
    else:
        service_time, opening, closing, distance = read_optw.round_to_first(
            service_time, opening, closing, distance
        )

    solve(
        vertices,
        service_time,
        profit,
        opening,
        closing,
        distance,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
    )
