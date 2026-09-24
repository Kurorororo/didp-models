#!/usr/bin/env python3

import argparse
import time

import didppy as dp
import read_graph_clear

start = time.perf_counter()


def create_model(n, node_weights, edge_weights):
    model = dp.Model()
    node = model.add_object_type(n)
    clean = model.add_set_var(node, [])
    all_nodes = model.create_set_const(node, [i for i in range(n)])
    edge_weight_matrix = [
        [
            edge_weights[i, j]
            if (i, j) in edge_weights
            else edge_weights[j, i]
            if (j, i) in edge_weights
            else 0
            for j in range(n)
        ]
        for i in range(n)
    ]
    a_b = model.add_int_table(
        [node_weights[i] + sum(edge_weight_matrix[i]) for i in range(n)]
    )
    b = model.add_int_table(edge_weight_matrix)
    contaminated = model.add_set_state_fun(clean.complement())

    model.add_base_case([all_nodes <= clean])

    name_to_node = {}
    transition_ids = []

    for i in range(n):
        name = f"sweep {i}"
        name_to_node[name] = i
        t = dp.Transition(
            name=name,
            cost=dp.max(
                dp.IntExpr.state_cost(),
                a_b[i] + b[clean, contaminated.remove(i)],
            ),
            effects=[(clean, clean.add(i))],
            preconditions=[~clean.contains(i)],
        )
        transition_ids.append(model.add_transition(t))

    model.add_dual_bound(0)

    # State functions
    clean_edge_weights = [model.add_int_state_fun(b[i, clean]) for i in range(n)]
    contaminated_edge_weights = [
        model.add_int_state_fun(b[i, contaminated]) for i in range(n)
    ]

    # Transition dominance
    for i in range(n):
        for j in range(n):
            if i == j:
                continue

            condition1 = (
                node_weights[i] + contaminated_edge_weights[i]
                <= node_weights[j] + contaminated_edge_weights[j]
            )
            condition2 = contaminated_edge_weights[i] <= clean_edge_weights[i]

            model.add_transition_dominance(
                transition_ids[i],
                transition_ids[j],
                conditions=[condition1, condition2],
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
):
    options = dict(time_limit=time_limit, quiet=False, f_operator=dp.FOperator.Max)
    if solver_name == "CAASDy":
        solver = dp.CAASDy(model, **options)
    elif solver_name == "CABS":
        solver = dp.CABS(
            model, initial_beam_size=initial_beam_size, threads=threads, **options
        )
    elif solver_name == "LNBS":
        solver = dp.LNBS(
            model,
            f_operator=dp.FOperator.Max,
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
        sequence = []

        for t in solution.transitions:
            sequence.append(name_to_node[t.name])

        return sequence, solution.cost, solution.best_bound, solution.is_optimal, False


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

    n, a, b = read_graph_clear.read(args.input)
    model, name_to_node = create_model(n, a, b)
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_node,
        args.config,
        args.history,
        time_limit=args.time_out,
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
    )

    if is_infeasible:
        print("The problem is infeasible.")
    else:
        print(f"best bound: {bound}")

        if cost is not None:
            print(solution)
            print(f"cost: {cost}")

            if is_optimal:
                print(f"optimal cost: {cost}")

            validation_result = read_graph_clear.validate(n, a, b, solution, cost)

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
