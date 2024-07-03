#!/usr/bin/env python3

import argparse
import math
import time

import didppy as dp
import read_optw

start = time.perf_counter()


def compute_shortest_distance(distance, service_time):
    vertices = list(range(len(distance)))
    shortest_distance = [
        [distance[i][j] + service_time[i] for j in vertices] for i in vertices
    ]

    for k in vertices:
        if k == 0:
            continue

        for i in vertices:
            if k == i:
                continue
            for j in vertices:
                if k == j or i == j:
                    continue

                d = shortest_distance[i][k] + shortest_distance[k][j]

                if shortest_distance[i][j] > d:
                    shortest_distance[i][j] = d

    return shortest_distance


def create_model(
    vertices,
    service_time,
    profit,
    opening,
    closing,
    distance,
    epsilon=1e-6,
    blind=False,
):
    model = dp.Model(maximize=True)

    node = model.add_object_type(number=len(vertices))
    unvisited = model.add_set_var(object_type=node, target=vertices[1:])
    location = model.add_element_var(object_type=node, target=0)
    time = model.add_int_resource_var(target=0, less_is_better=True)

    distance_matrix = [
        [service_time[i] + distance[i][j] for j in vertices] for i in vertices
    ]
    distance_table = model.add_int_table(distance_matrix)

    shortest_distance = compute_shortest_distance(distance, service_time)
    shortest_distance_table = model.add_int_table(shortest_distance)

    shortest_return_distance = [
        [shortest_distance[i][j] + shortest_distance[j][0] for j in vertices]
        for i in vertices
    ]
    shortest_return_distance_table = model.add_int_table(shortest_return_distance)
    distance_plus_shortest_return_table = model.add_int_table(
        [
            [distance_matrix[i][j] + shortest_distance[j][0] for j in vertices]
            for i in vertices
        ]
    )

    model.add_base_case(
        [unvisited.is_empty(), time + distance_table[location, 0] <= closing[0]]
    )

    for i in vertices[1:]:
        name = "remove {}".format(i)
        remove = dp.Transition(
            name=name,
            cost=dp.IntExpr.state_cost(),
            effects=[(unvisited, unvisited.remove(i))],
            preconditions=[
                unvisited.contains(i),
                (time + shortest_distance_table[location, i] > closing[i])
                | (time + shortest_return_distance_table[location, i] > closing[0]),
            ],
        )
        model.add_transition(remove, forced=True)

    for i in vertices[1:]:
        name = "clear {}".format(i)
        clear = dp.Transition(
            name=name,
            cost=dp.IntExpr.state_cost(),
            effects=[(unvisited, unvisited.remove(i))],
            preconditions=[unvisited.contains(i)]
            + [
                ~unvisited.contains(j)
                | (time + distance_table[location, j] > closing[j])
                | (time + distance_plus_shortest_return_table[location, j] > closing[0])
                for j in vertices[1:]
            ],
        )
        model.add_transition(clear, forced=True)

    name_to_node = {}

    for i in vertices[1:]:
        name = "visit {}".format(i)
        name_to_node[name] = i
        set_effect = unvisited.remove(i)

        visit = dp.Transition(
            name=name,
            cost=profit[i] + dp.IntExpr.state_cost(),
            effects=[
                (unvisited, set_effect),
                (location, i),
                (time, dp.max(time + distance_table[location, i], opening[i])),
            ],
            preconditions=[
                unvisited.contains(i),
                time + distance_table[location, i] <= closing[i],
                time + distance_plus_shortest_return_table[location, i] <= closing[0],
            ],
        )
        model.add_transition(visit)

    if not blind:
        model.add_dual_bound(
            sum(
                (
                    unvisited.contains(i)
                    & (time + shortest_distance_table[location, i] <= closing[i])
                    & (time + shortest_return_distance_table[location, i] <= closing[0])
                ).if_then_else(profit[i], 0)
                for i in vertices[1:]
            )
        )

        min_distance_from = [
            min(distance_matrix[i][j] for j in vertices if i != j) for i in vertices
        ]
        min_distance_from_table = model.add_int_table(min_distance_from)
        efficiency_from = [p / c + epsilon for p, c in zip(profit, min_distance_from)]

        max_efficiency_from = None

        for i in vertices[1:]:
            efficiency_i = (
                unvisited.contains(i)
                & (time + shortest_distance_table[location, i] <= closing[i])
                & (time + shortest_return_distance_table[location, i] <= closing[0])
            ).if_then_else(efficiency_from[i], 0)

            if max_efficiency_from is None:
                max_efficiency_from = efficiency_i
            else:
                max_efficiency_from = dp.max(max_efficiency_from, efficiency_i)

        model.add_dual_bound(
            math.floor(
                (closing[0] - time - min_distance_from_table[location])
                * max_efficiency_from
            )
        )

        min_distance_to = [
            min(distance_matrix[i][j] for i in vertices if i != j) for j in vertices
        ]
        efficiency_to = model.add_float_table(
            [profit[i] / min_distance_to[i] + epsilon for i in vertices]
        )

        max_efficiency_to = None

        for i in vertices[1:]:
            efficiency_i = (
                unvisited.contains(i)
                & (time + shortest_distance_table[location, i] <= closing[i])
                & (time + shortest_return_distance_table[location, i] <= closing[0])
            ).if_then_else(efficiency_to[i], 0)

            if max_efficiency_to is None:
                max_efficiency_to = efficiency_i
            else:
                max_efficiency_to = dp.max(max_efficiency_to, efficiency_i)

        model.add_dual_bound(
            math.floor((closing[0] - time - min_distance_to[0]) * max_efficiency_to)
        )

    return model, name_to_node


def solve(
    model,
    name_to_node,
    solver_name,
    history,
    time_limit=None,
    seed=2023,
    initial_beam_size=1,
    threads=1,
    parallel_type=0,
):
    if solver_name == "LNBS":
        if parallel_type == 2:
            parallelization_method = dp.BeamParallelizationMethod.Sbs
        elif parallel_type == 1:
            parallelization_method = dp.BeamParallelizationMethod.Hdbs1
        else:
            parallelization_method = dp.BeamParallelizationMethod.Hdbs2

        solver = dp.LNBS(
            model,
            time_limit=time_limit,
            quiet=False,
            seed=seed,
            parallelization_method=parallelization_method,
            threads=threads,
        )
    elif solver_name == "DD-LNS":
        solver = dp.DDLNS(model, time_limit=time_limit, quiet=False, seed=seed)
    elif solver_name == "FR":
        solver = dp.ForwardRecursion(model, time_limit=time_limit, quiet=False)
    elif solver_name == "BrFS":
        solver = dp.BreadthFirstSearch(model, time_limit=time_limit, quiet=False)
    elif solver_name == "CAASDy":
        solver = dp.CAASDy(model, time_limit=time_limit, quiet=False)
    elif solver_name == "DFBB":
        solver = dp.DFBB(model, time_limit=time_limit, quiet=False)
    elif solver_name == "CBFS":
        solver = dp.CBFS(model, time_limit=time_limit, quiet=False)
    elif solver_name == "ACPS":
        solver = dp.ACPS(model, time_limit=time_limit, quiet=False)
    elif solver_name == "APPS":
        solver = dp.APPS(model, time_limit=time_limit, quiet=False)
    elif solver_name == "DBDFS":
        solver = dp.DBDFS(model, time_limit=time_limit, quiet=False)
    else:
        if parallel_type == 2:
            parallelization_method = dp.BeamParallelizationMethod.Sbs
        elif parallel_type == 1:
            parallelization_method = dp.BeamParallelizationMethod.Hdbs1
        else:
            parallelization_method = dp.BeamParallelizationMethod.Hdbs2

        solver = dp.CABS(
            model,
            initial_beam_size=initial_beam_size,
            threads=threads,
            parallelization_method=parallelization_method,
            time_limit=time_limit,
            quiet=False,
        )

    if solver_name == "FR":
        solution = solver.search()
    else:
        with open(history, "w") as f:
            is_terminated = False

            while not is_terminated:
                solution, is_terminated = solver.search_next()

                if solution.cost is not None:
                    f.write(
                        "{}, {}\n".format(time.perf_counter() - start, solution.cost)
                    )
                    f.flush()

    print("Search time: {}s".format(solution.time))

    if solution.is_infeasible:
        print("The problem is infeasible")

        return None, None
    else:
        tour = [0]

        for t in solution.transitions:
            if t.name in name_to_node:
                tour.append(name_to_node[t.name])

        tour.append(0)

        print(" ".join(map(str, tour[1:-1])))

        print("Search time: {}s".format(solution.time))
        print("Expanded: {}".format(solution.expanded))
        print("Generated: {}".format(solution.generated))
        print("cost: {}".format(solution.cost))
        print("best bound: {}".format(solution.best_bound))

        if solution.is_optimal:
            print("optimal cost: {}".format(solution.cost))

        return tour, solution.cost


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--time-out", default=1800, type=int)
    parser.add_argument("--history", default="history.csv", type=str)
    parser.add_argument("--config", default="CABS", type=str)
    parser.add_argument("--seed", default=2023, type=int)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--initial-beam-size", default=1, type=int)
    parser.add_argument("--parallel-type", default=0, type=int)
    parser.add_argument("--round-to-second", action="store_true")
    parser.add_argument("--epsilon", type=float, default=1e-6)
    parser.add_argument("--blind", action="store_true")
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

    model, name_to_node = create_model(
        vertices,
        service_time,
        profit,
        opening,
        closing,
        distance,
        epsilon=args.epsilon,
        blind=args.blind,
    )

    tour, cost = solve(
        model,
        name_to_node,
        args.config,
        args.history,
        time_limit=args.time_out,
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
        parallel_type=args.parallel_type,
    )

    if cost is not None and read_optw.validate_optw(
        service_time, profit, opening, closing, distance, tour, cost
    ):
        print("The solution is valid.")
    else:
        print("The solution is invalid.")
