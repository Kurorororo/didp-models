#! /usr/bin/env python3

import argparse
import math
import time

import gurobipy as gp
import read_salbp1

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
    number_of_tasks,
    cycle_time,
    task_times,
    predecessors,
    followers,
    use_all_followers=False,
    time_limit=None,
    threads=1,
    verbose=False,
    history=None,
):
    tasks = list(range(1, number_of_tasks + 1))
    _, m_ub = compute_m_bounds(number_of_tasks, cycle_time, task_times)
    stations = list(range(1, m_ub + 1))
    all_predecessors = compute_all_predecessors(tasks, predecessors)
    all_followers = compute_all_followers(tasks, followers)
    earliest = {}
    latest = {}
    x_indices = []
    for i in tasks:
        earliest[i] = compute_earliest_station(
            i, cycle_time, task_times, all_predecessors
        )
        latest[i] = compute_latest_station(
            i, cycle_time, task_times, all_followers, m_ub
        )
        x_indices += [(s, i) for s in range(earliest[i], latest[i] + 1)]

    model = gp.Model()
    model.setParam("Threads", threads)
    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)
    if not verbose:
        model.setParam("OutputFlag", 0)

    x = model.addVars(x_indices, vtype=gp.GRB.BINARY)
    y = model.addVars(stations, vtype=gp.GRB.BINARY, obj=1)

    model.addConstrs(
        gp.quicksum(
            task_times[i] * x[s, i] for i in tasks if earliest[i] <= s <= latest[i]
        )
        <= cycle_time * y[s]
        for s in stations
    )
    model.addConstrs(
        gp.quicksum(x[s, i] for s in stations if earliest[i] <= s <= latest[i]) == 1
        for i in tasks
    )
    model.addConstrs(
        gp.quicksum(
            x[u, i]
            for u in stations
            if earliest[i] <= u <= latest[i]
            and u >= compute_latest_station(i, cycle_time, task_times, all_followers, s)
        )
        <= y[s]
        for s in stations
        for i in tasks
    )
    model.addConstrs(
        gp.quicksum(
            x[s, i] for s in stations if earliest[i] <= s <= latest[i] and s <= k
        )
        >= gp.quicksum(
            x[s, j] for s in stations if earliest[j] <= s <= latest[j] and s <= k
        )
        for i in tasks
        for j in (all_followers[i] if use_all_followers else followers[i])
        for k in stations
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
        solution = []
        for s in stations:
            tasks_in_station = []
            for i in tasks:
                if earliest[i] <= s <= latest[i] and x[s, i].X > 0.5:
                    tasks_in_station.append(i)
            if len(tasks_in_station) > 0:
                solution.append(tasks_in_station)
        cost = round(model.objVal)
        print(solution)
        print("cost: {}".format(cost))
        validation_result = read_salbp1.validate(
            number_of_tasks, cycle_time, task_times, predecessors, solution, cost
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


def compute_m_bounds(number_of_tasks, cycle_time, task_times):
    lb = math.ceil(sum(task_times.values()) / cycle_time)
    ub = min(2 * lb, number_of_tasks)
    return lb, ub


def compute_all_predecessors(tasks, predecessors):
    all_predecessors = {}
    for i in tasks:
        predecessor_set = set()
        for j in predecessors[i]:
            predecessor_set.add(j)
            predecessor_set.update(all_predecessors[j])
        all_predecessors[i] = sorted(list(predecessor_set))
    return all_predecessors


def compute_all_followers(tasks, followers):
    all_followers = {}
    for i in reversed(tasks):
        follower_set = set()
        for j in followers[i]:
            follower_set.add(j)
            follower_set.update(all_followers[j])
        all_followers[i] = sorted(list(follower_set))
    return all_followers


def compute_earliest_station(i, cycle_time, task_times, predecessors):
    return math.ceil(
        (task_times[i] + sum(task_times[j] for j in predecessors[i])) / cycle_time
    )


def compute_latest_station(i, cycle_time, task_times, followers, m):
    return (
        m
        + 1
        - math.ceil(
            (task_times[i] + sum(task_times[j] for j in followers[i])) / cycle_time
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--threads", "-t", type=int, default=1)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--all-followers", action="store_true")
    parser.add_argument("--history", type=str)
    args = parser.parse_args()

    number_of_tasks, cycle_time, task_times, predecessors, followers = read_salbp1.read(
        args.input
    )
    solve(
        number_of_tasks,
        cycle_time,
        task_times,
        predecessors,
        followers,
        use_all_followers=args.all_followers,
        time_limit=args.time_out,
        threads=args.threads,
        verbose=args.verbose,
        history=args.history,
    )
