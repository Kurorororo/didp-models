#! /usr/bin/env python3

import argparse
import math
import time

import docplex.cp.model as cp

import read_salbp1


start = time.perf_counter()


def solve(
    number_of_tasks,
    cycle_time,
    task_times,
    predecessors,
    followers,
    pack,
    time_limit=None,
    threads=1,
    history=None,
):
    tasks = list(range(1, number_of_tasks + 1))
    m_lb, m_ub = compute_m_bounds(number_of_tasks, cycle_time, task_times)
    all_predecessors, all_predecessors_set = compute_all_predecessors(
        tasks, predecessors
    )
    all_followers, _ = compute_all_followers(tasks, followers)

    e = {
        i: math.ceil(
            (task_times[i] + sum(task_times[j] for j in all_predecessors[i]))
            / cycle_time
        )
        for i in tasks
    }
    lb = {
        i: math.floor(
            (task_times[i] - 1 + sum(task_times[j] for j in all_followers[i]))
            / cycle_time
        )
        for i in tasks
    }
    d = {
        (i, j): math.floor(
            (
                task_times[i]
                + task_times[j]
                - 1
                + sum(
                    task_times[k]
                    for k in all_followers[i]
                    if k in all_predecessors_set[j]
                )
            )
            / cycle_time
        )
        for j in tasks
        for i in all_predecessors[j]
    }

    m = cp.integer_var(m_lb, m_ub)
    size = [task_times[i] for i in tasks]
    where = [cp.integer_var(e[i] - 1, m_ub - 1) for i in tasks]

    model = cp.CpoModel()

    for i in tasks:
        model.add(where[i - 1] <= m - 1 - lb[i])

    for j in tasks:
        for i in all_predecessors[j]:
            fire = all(
                k not in all_predecessors_set[j] or d[i, j] > d[i, k] + d[k, j]
                for k in all_followers[i]
            )
            if fire:
                model.add(where[i - 1] + d[i, j] <= where[j - 1])

    if pack:
        load = cp.integer_var_list(m_ub, 0, cycle_time)
        model.add(cp.pack(load, where, size))
    else:
        for j in range(m_ub):
            model.add(
                cp.sum((where[i - 1] == j) * task_times[i] for i in tasks) <= cycle_time
            )

    model.add(cp.minimize(m))

    if args.history is None:
        result = model.solve(
            TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
        )
    else:
        solver = cp.CpoSolver(
            model, TimeLimit=time_limit, Workers=threads, LogVerbosity="Quiet"
        )
        with open(history, "w") as f:
            is_new_solution = True
            while is_new_solution:
                result = solver.search_next()
                is_new_solution = result.is_new_solution()

                if is_new_solution:
                    f.write(
                        "{}, {}\n".format(
                            time.perf_counter() - start, result.get_objective_value()
                        )
                    )

    if result.is_solution():
        cost = result.get_objective_value()
        station_to_tasks = {}
        for i in tasks:
            station = result[where[i - 1]] + 1

            if station not in station_to_tasks:
                station_to_tasks[station] = []

            station_to_tasks[station].append(i)

        solution = [station_to_tasks[station] for station in range(1, cost + 1)]
        print(solution)
        print("cost: {}".format(cost))
        validation_result = read_salbp1.validate(
            number_of_tasks, cycle_time, task_times, predecessors, solution, round(cost)
        )
        if validation_result:
            print("The solution is valid.")

            if result.is_solution_optimal():
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(result.get_objective_gap()))
                print("best bound: {}".format(result.get_objective_bound()))
        else:
            print("The solution is invalid.")
    elif result.get_solve_status() == "infeasible":
        print("The problem is infeasible.")


def compute_m_bounds(number_of_tasks, cycle_time, task_times):
    lb = math.ceil(sum(task_times.values()) / cycle_time)
    ub = min(2 * lb, number_of_tasks)
    return lb, ub


def compute_all_predecessors(tasks, predecessors):
    all_predecessors = {}
    all_predecessors_set = {}
    for i in tasks:
        predecessor_set = set()
        for j in predecessors[i]:
            predecessor_set.add(j)
            predecessor_set.update(all_predecessors[j])
        all_predecessors_set[i] = predecessor_set
        all_predecessors[i] = sorted(list(predecessor_set))
    return all_predecessors, all_predecessors_set


def compute_all_followers(tasks, followers):
    all_followers = {}
    all_followers_set = {}
    for i in reversed(tasks):
        follower_set = set()
        for j in followers[i]:
            follower_set.add(j)
            follower_set.update(all_followers[j])
        all_followers_set[i] = follower_set
        all_followers[i] = sorted(list(follower_set))
    return all_followers, all_followers_set


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
    parser.add_argument("--time-out", default=1800, type=float)
    parser.add_argument("--pack", action="store_true")
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
        args.pack,
        time_limit=args.time_out,
        threads=args.threads,
        history=args.history,
    )
