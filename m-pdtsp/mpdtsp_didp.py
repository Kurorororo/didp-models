#!/usr/bin/env python3

import argparse
import time

import didppy as dp
import read_tsplib
from mpdtsp_util import (
    check_edge,
    compute_not_inferred_precedence,
    compute_precedence,
    compute_predecessors_and_successors,
)

start = time.perf_counter()


def compute_min_distance_to(nodes, edges):
    max_distance = max(edges.values())
    result = [
        min([max_distance] + [edges[i, j] for i in nodes if (i, j) in edges])
        for j in nodes
    ]
    result[0] = 0

    return result


def compute_min_distance_from(nodes, edges):
    max_distance = max(edges.values())
    result = [
        min([max_distance] + [edges[i, j] for j in nodes if (i, j) in edges])
        for i in nodes
    ]
    result[-1] = 0

    return result


def create_model(n, nodes, edges, capacity, items, demand):
    precedence_edges = compute_precedence(nodes, items, demand)
    (
        predecessors,
        successors,
        transitive_precedence_edges,
    ) = compute_predecessors_and_successors(nodes, precedence_edges)
    not_inferred_precedence_edges = compute_not_inferred_precedence(
        predecessors, successors, precedence_edges
    )
    filtered_edges = {
        (i, j): w
        for (i, j), w in edges.items()
        if w >= 0
        and i != j
        and check_edge(i, j, nodes, not_inferred_precedence_edges, capacity)
        and (j, i) not in transitive_precedence_edges
        and (
            (i, j) not in transitive_precedence_edges
            or (i, j) in not_inferred_precedence_edges
        )
    }

    if len(filtered_edges) == 0:
        return None, None

    model = dp.Model()

    customer = model.add_object_type(number=n)
    unvisited = model.add_set_var(object_type=customer, target=list(range(1, n - 1)))
    location = model.add_element_var(object_type=customer, target=0)
    load = model.add_int_resource_var(target=0, less_is_better=True)

    demand = model.add_int_table([sum(demand[i, j] for j in items) for i in nodes])
    connected = model.add_bool_table(
        [[(i, j) in filtered_edges for j in nodes] for i in nodes]
    )
    predecessors = model.add_set_table(
        [[p - 1 for p in predecessors[i]] for i in nodes], object_type=customer
    )
    distance = model.add_int_table(
        [
            [filtered_edges[i, j] if (i, j) in filtered_edges else 0 for j in nodes]
            for i in nodes
        ]
    )

    name_to_node = {}
    state_cost = dp.IntExpr.state_cost()
    transitions = []

    for i in range(1, n - 1):
        name = "visit {}".format(nodes[i])
        name_to_node[name] = nodes[i]
        visit = dp.Transition(
            name=name,
            cost=distance[location, i] + state_cost,
            effects=[
                (unvisited, unvisited.remove(i)),
                (location, i),
                (load, load + demand[i]),
            ],
            preconditions=[
                connected[location, i],
                load + demand[i] <= capacity,
                unvisited.contains(i),
                unvisited.isdisjoint(predecessors[i]),
            ],
        )
        model.add_transition(visit)
        transitions.append(visit)

    name = "finish"
    name_to_node[name] = nodes[n - 1]
    finish = dp.Transition(
        name=name,
        cost=distance[location, n - 1] + state_cost,
        effects=[(location, n - 1)],
        preconditions=[connected[location, n - 1], unvisited.is_empty()],
    )
    model.add_transition(finish)
    transitions.append(finish)

    model.add_base_case([location == n - 1, unvisited.is_empty()])

    min_distance_to = compute_min_distance_to(nodes, filtered_edges)
    min_distance_to = model.add_int_table(min_distance_to)
    model.add_dual_bound(
        min_distance_to[unvisited]
        + (location == n - 1).if_then_else(0, min_distance_to[n - 1])
    )

    min_distance_from = compute_min_distance_from(nodes, filtered_edges)
    min_distance_from = model.add_int_table(min_distance_from)
    model.add_dual_bound(min_distance_from[unvisited] + min_distance_from[location])

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
            initial_beam_size=initial_beam_size,
            seed=seed,
            parallelization_method=parallelization_method,
            threads=threads,
            time_limit=time_limit,
            quiet=False,
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
    print("Expanded: {}".format(solution.expanded))
    print("Generated: {}".format(solution.generated))

    if solution.is_infeasible:
        return None, None, None, False, True
    else:
        permutation = [1] + [name_to_node[t.name] for t in solution.transitions]

        return (
            permutation,
            solution.cost,
            solution.best_bound,
            solution.is_optimal,
            False,
        )


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
    args = parser.parse_args()

    n, nodes, edges, capacity, m, items, demand, _ = read_tsplib.read_mpdtsp(args.input)

    model, name_to_node = create_model(n, nodes, edges, capacity, items, demand)

    if model is None:
        print("The problem is infeasible.")
    else:
        solution, cost, bound, is_optimal, is_infeasible = solve(
            model,
            name_to_node,
            args.config,
            args.history,
            args.time_out,
            args.seed,
            threads=args.threads,
            initial_beam_size=args.initial_beam_size,
        )

        if is_infeasible:
            print("The problem is infeasible.")
        else:
            print("best bound: {}".format(bound))

            if cost is not None:
                print(" ".join(map(str, solution)))
                print("cost: {}".format(cost))

                if is_optimal:
                    print("optimal cost: {}".format(cost))

                validation_result = read_tsplib.validate_mpdtsp(
                    solution, cost, nodes, edges, capacity, items, demand
                )
                if validation_result:
                    print("The solution is valid.")
                else:
                    print("The solution is invalid.")
