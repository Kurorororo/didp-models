#!/usr/bin/env python3

import argparse
import time

import docplex.cp.model as cp
import read_optw

start = time.perf_counter()


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
    model = cp.CpoModel()

    y = []

    for i in vertices:
        if i == 0:
            y.append(
                cp.interval_var(start=opening[0], length=service_time[0], name="0")
            )
        else:
            y.append(
                cp.interval_var(
                    start=(opening[i], closing[i]),
                    length=service_time[i],
                    optional=True,
                    name=str(i),
                )
            )

    y.append(
        cp.interval_var(
            start=(opening[0], closing[0]), length=service_time[0], name="0"
        )
    )
    q = cp.sequence_var(y, types=vertices + [0])
    transition = cp.transition_matrix(distance)
    model.add(cp.no_overlap(q, transition, is_direct=True))
    model.add(cp.first(q, y[0]))
    model.add(cp.last(q, y[-1]))
    model.add(
        cp.maximize(
            cp.sum([cp.presence_of(y[i]) * profit[i] for i in vertices if i != 0])
        )
    )

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

    print("Search time: {}s".format(result.get_solve_time()))

    if result.is_solution():
        solution = [int(v.get_name()) for v in result[q]]
        cost = result.get_objective_value()
        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_optw.validate_optw(
            service_time, profit, opening, closing, distance, solution, cost
        )

        if validation_result:
            print("The solution is valid.")
            if result.is_solution_optimal():
                print("optimal cost: {}".format(cost))
            else:
                print("gap: {}".format(result.get_objective_gap()))
                print("best bound: {}".format(result.get_objective_bound()))
        else:
            print("The solution is invalid")
    elif result.get_solve_status() == "Infeasible":
        print("The problem is infeasible.")


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
