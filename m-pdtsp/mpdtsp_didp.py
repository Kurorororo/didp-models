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
        return None, None, None

    model = dp.Model()

    customer = model.add_object_type(number=n)
    unvisited = model.add_set_var(object_type=customer, target=list(range(1, n - 1)))
    location = model.add_element_var(object_type=customer, target=0)
    load = model.add_int_resource_var(target=0, less_is_better=True)

    demand = model.add_int_table([sum(demand[i, j] for j in items) for i in nodes])
    connected = model.add_bool_table(
        [[(i, j) in filtered_edges for j in nodes] for i in nodes]
    )
    indices = {v: i for i, v in enumerate(nodes)}
    predecessors = model.add_set_table(
        [[indices[p] for p in predecessors[i]] for i in nodes], object_type=customer
    )
    distance = model.add_int_table(
        [
            [filtered_edges[i, j] if (i, j) in filtered_edges else 0 for j in nodes]
            for i in nodes
        ]
    )

    name_to_node = {"start": nodes[0], "goal": nodes[-1]}
    state_cost = dp.IntExpr.state_cost()

    for i in range(1, n - 1):
        name = f"visit {nodes[i]}"
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

    model.add_base_case(
        [unvisited.is_empty(), connected[location, n - 1]],
        cost=distance[location, n - 1],
    )
    # A finite penalty connects impossible suffixes without an MST panic.
    # It exceeds the cost of every feasible Hamiltonian completion.
    infinity = n * max(filtered_edges.values(), default=0) + 1
    mst_distance = model.add_int_table(
        [
            [0 if i == j else filtered_edges.get((i, j), infinity) for j in nodes]
            for i in nodes
        ]
    )
    min_goal = min(
        (cost for (i, j), cost in filtered_edges.items() if j == nodes[-1]),
        default=infinity,
    )
    model.add_dual_bound(
        dp.minimum_spanning_tree(unvisited.add(location), mst_distance) + min_goal
    )

    return model, name_to_node, infinity


def solve(
    model,
    name_to_node,
    solver_name,
    history,
    primal_bound,
    time_limit=None,
    seed=2023,
    initial_beam_size=1,
    threads=1,
):
    options = dict(time_limit=time_limit, quiet=False, primal_bound=primal_bound)
    if solver_name == "CAASDy":
        solver = dp.CAASDy(model, **options)
    elif solver_name == "CABS":
        solver = dp.CABS(
            model, initial_beam_size=initial_beam_size, threads=threads, **options
        )
    elif solver_name == "LNBS":
        solver = dp.LNBS(
            model,
            initial_beam_size=initial_beam_size,
            threads=threads,
            seed=seed,
            **options,
        )
    else:
        raise ValueError(f"Unknown solver: {solver_name}")

    with open(history, "w") as f:
        is_terminated = False

        while not is_terminated:
            solution, is_terminated = solver.search_next()

            if solution.cost is not None:
                f.write(f"{time.perf_counter() - start}, {solution.cost}\n")
                f.flush()

    print(f"Search time: {solution.time}s")
    print(f"Expanded: {solution.expanded}")
    print(f"Generated: {solution.generated}")

    if solution.is_infeasible:
        return None, None, None, False, True
    else:
        permutation = (
            [name_to_node["start"]]
            + [name_to_node[t.name] for t in solution.transitions]
            + [name_to_node["goal"]]
        )

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
    parser.add_argument("--config", choices=["CAASDy", "CABS", "LNBS"], default="CABS")
    parser.add_argument("--seed", default=2023, type=int)
    parser.add_argument("--threads", default=1, type=int)
    parser.add_argument("--initial-beam-size", default=1, type=int)
    args = parser.parse_args()

    n, nodes, edges, capacity, m, items, demand, _ = read_tsplib.read_mpdtsp(args.input)

    model, name_to_node, infinity = create_model(
        n, nodes, edges, capacity, items, demand
    )

    if model is None:
        print("The problem is infeasible.")
    else:
        solution, cost, bound, is_optimal, is_infeasible = solve(
            model,
            name_to_node,
            args.config,
            args.history,
            infinity,
            args.time_out,
            args.seed,
            threads=args.threads,
            initial_beam_size=args.initial_beam_size,
        )

        if is_infeasible:
            print("The problem is infeasible.")
        else:
            print(f"best bound: {bound}")

            if cost is not None:
                print(" ".join(map(str, solution)))
                print(f"cost: {cost}")

                if is_optimal:
                    print(f"optimal cost: {cost}")

                validation_result = read_tsplib.validate_mpdtsp(
                    solution, cost, nodes, edges, capacity, items, demand
                )
                if validation_result:
                    print("The solution is valid.")
                else:
                    print("The solution is invalid.")
