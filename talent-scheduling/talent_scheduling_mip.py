#!/usr/bin/env python3

import argparse
import time

import gurobipy as gp

import read_talent_scheduling


start = time.perf_counter()


def get_callback(file, base_cost):
    def dump_solution(model, where):
        if where == gp.GRB.Callback.MIPSOL:
            file.write(
                "{}, {}\n".format(
                    time.perf_counter() - start,
                    round(model.cbGet(gp.GRB.Callback.MIPSOL_OBJ)) + base_cost,
                )
            )

    return dump_solution


def solve(
    actor_to_scenes,
    actor_to_cost,
    scene_to_duration,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    n = len(scene_to_duration)
    m = len(actor_to_cost)
    scenes = list(range(n))
    actors = list(range(m))

    scene_pairs = [(k, j) for k in scenes for j in scenes if k != j]

    negative_actor_to_cost = [-c for c in actor_to_cost]

    big_l = sum(scene_to_duration)

    model = gp.Model()

    x_start = model.addVars(scenes, vtype=gp.GRB.BINARY)
    x = model.addVars(scene_pairs, vtype=gp.GRB.BINARY)
    x_end = model.addVars(scenes, vtype=gp.GRB.BINARY)
    e = model.addVars(actors, vtype=gp.GRB.INTEGER, lb=0, obj=negative_actor_to_cost)
    l = model.addVars(actors, vtype=gp.GRB.INTEGER, lb=0, obj=actor_to_cost)
    t_start = model.addVar(vtype=gp.GRB.INTEGER, lb=0)
    t = model.addVars(scenes, vtype=gp.GRB.INTEGER, lb=0)
    t_end = model.addVar(vtype=gp.GRB.INTEGER, lb=0)
    z_start = model.addVars(scenes, vtype=gp.GRB.CONTINUOUS, lb=0)
    z = model.addVars(scene_pairs, vtype=gp.GRB.CONTINUOUS, lb=0)
    z_end = model.addVars(scenes, vtype=gp.GRB.CONTINUOUS, lb=0)

    model.addConstr(gp.quicksum(x_start[j] for j in scenes) == 1)
    model.addConstr(gp.quicksum(x_end[k] for k in scenes) == 1)
    model.addConstrs(
        gp.quicksum(x[k, j] for j in scenes if k != j) + x_end[k] == 1 for k in scenes
    )
    model.addConstrs(
        x_start[j] + gp.quicksum(x[k, j] for k in scenes if k != j) == 1 for j in scenes
    )
    model.addConstr(t_start == 0)
    model.addConstrs(
        e[i] <= t[j] for i in actors for j in scenes if actor_to_scenes[i][j] == 1
    )
    model.addConstrs(
        t[j] + scene_to_duration[j] - 1 <= l[i]
        for i in actors
        for j in scenes
        if actor_to_scenes[i][j] == 1
    )

    model.addConstrs(z_start[j] <= t_start for j in scenes)
    model.addConstrs(z_start[j] >= t[j] + big_l * (x_start[j] - 1) for j in scenes)
    model.addConstrs(z_start[j] <= big_l * x_start[j] for j in scenes)
    model.addConstr(gp.quicksum(z_start[j] for j in scenes) == t_start)

    model.addConstrs(z_end[k] <= t_end for k in scenes)
    model.addConstrs(z_end[k] >= t[k] + big_l * (x_end[k] - 1) for k in scenes)
    model.addConstrs(z_end[k] <= big_l * x_end[k] for k in scenes)
    model.addConstr(gp.quicksum(z_end[k] for k in scenes) == t_end)

    model.addConstrs(z[k, j] <= t[j] for k, j in scene_pairs)
    model.addConstrs(z[k, j] >= t[j] + big_l * (x[k, j] - 1) for k, j in scene_pairs)
    model.addConstrs(z[k, j] <= big_l * x[k, j] for k, j in scene_pairs)
    model.addConstrs(
        gp.quicksum(z[k, j] for j in scenes if k != j) + z_end[k]
        == t[k] + scene_to_duration[k]
        for k in scenes
    )

    model.setParam("Threads", threads)

    base_cost = sum(actor_to_cost[i] for i in actors)

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

    solution = None
    cost = None
    is_optimal = status == gp.GRB.OPTIMAL
    gap = None
    best_bound = None

    if status == gp.GRB.INFEASIBLE:
        print("infeasible")
    else:
        best_bound = model.getAttr("ObjBound")

    if sol_count > 0:
        start_days = []
        for i in scenes:
            start_days.append((t[i].X, i))
        solution = [i for _, i in sorted(start_days)]
        cost = round(model.objVal) + base_cost
        gap = model.getAttr("MIPGap")

    return solution, cost, is_optimal, gap, best_bound


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    _, actor_to_scenes, actor_to_cost, scene_to_duration = read_talent_scheduling.read(
        args.input
    )
    (
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
        single_actor_cost,
        scene_to_original,
    ) = read_talent_scheduling.simplify(
        actor_to_scenes, actor_to_cost, scene_to_duration
    )
    solution, cost, is_optimal, gap, best_bound = solve(
        simplified_actor_to_scenes,
        simplified_actor_to_cost,
        simplified_scene_to_duration,
        time_limit=args.time_out,
        threads=args.threads,
        verbose=args.verbose,
        history=args.history,
    )

    if solution is not None:
        solution, reconstructed_cost = read_talent_scheduling.reconstruct_solution(
            solution, cost, single_actor_cost, scene_to_original
        )

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_talent_scheduling.validate(
            solution,
            reconstructed_cost,
            actor_to_scenes,
            actor_to_cost,
            scene_to_duration,
        )

        if validation_result:
            print("The solution is valid.")
            if is_optimal:
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(gap))
                print("best bound: {}".format(best_bound))
        else:
            print("The solution is invalid.")
