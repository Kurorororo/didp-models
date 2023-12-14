#! /usr/bin/env python3

import argparse
import math
import time

import didppy as dp
import read_salbp1

start = time.perf_counter()


def create_model(number_of_tasks, cycle_time, task_times, predecessors):
    model = dp.Model()
    task = model.add_object_type(number_of_tasks)
    uncompleted = model.add_set_var(task, [i for i in range(number_of_tasks)])
    idle_time = model.add_int_resource_var(0, less_is_better=False)
    task_time_table = model.add_int_table(
        [task_times[i + 1] for i in range(number_of_tasks)]
    )
    predecessors_table = model.add_set_table(
        [[j - 1 for j in predecessors[i + 1]] for i in range(number_of_tasks)],
        object_type=task,
    )
    lb2_weight1 = model.add_int_table(
        [1 if task_times[i + 1] > cycle_time / 2 else 0 for i in range(number_of_tasks)]
    )
    lb2_weight2 = model.add_float_table(
        [
            0.5 if task_times[i + 1] == cycle_time / 2 else 0
            for i in range(number_of_tasks)
        ]
    )
    lb3_weight = model.add_float_table(
        [
            1.0
            if task_times[i + 1] > cycle_time * 2 / 3
            else 2 / 3 // 0.001 / 1000
            if task_times[i + 1] == cycle_time * 2 / 3
            else 0.5
            if task_times[i + 1] > cycle_time / 3
            else 1 / 3 // 0.001 / 1000
            if task_times[i + 1] == cycle_time / 3
            else 0.0
            for i in range(number_of_tasks)
        ]
    )
    model.add_base_case([uncompleted.is_empty()])

    name_to_task = {}

    for i in range(number_of_tasks):
        name = "schedule {}".format(i)
        name_to_task[name] = i + 1
        t = dp.Transition(
            name=name,
            cost=dp.IntExpr.state_cost(),
            effects=[
                (uncompleted, uncompleted.remove(i)),
                (idle_time, idle_time - task_time_table[i]),
            ],
            preconditions=[
                uncompleted.contains(i),
                task_time_table[i] <= idle_time,
                uncompleted.isdisjoint(predecessors_table[i]),
            ],
        )
        model.add_transition(t)

    t = dp.Transition(
        name="open a new station",
        cost=dp.IntExpr.state_cost() + 1,
        effects=[(idle_time, cycle_time)],
        preconditions=[
            ~uncompleted.contains(i)
            | (task_time_table[i] > idle_time)
            | ~uncompleted.isdisjoint(predecessors_table[i])
            for i in range(number_of_tasks)
        ],
    )
    model.add_transition(t, forced=True)

    model.add_dual_bound(
        math.ceil((task_time_table[uncompleted] - idle_time) / cycle_time)
    )
    model.add_dual_bound(
        lb2_weight1[uncompleted]
        + math.ceil(lb2_weight2[uncompleted])
        - (idle_time >= cycle_time / 2).if_then_else(1, 0)
    )
    model.add_dual_bound(
        math.ceil(lb3_weight[uncompleted])
        - (idle_time >= cycle_time / 3).if_then_else(1, 0)
    )

    return model, name_to_task


def solve(
    model,
    name_to_task,
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
        assignment = []

        for t in solution.transitions:
            if t.name == "open a new station":
                assignment.append([])
            else:
                assignment[-1].append(name_to_task[t.name])

        return (
            assignment,
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

    number_of_tasks, cycle_time, task_times, predecessors, _ = read_salbp1.read(
        args.input
    )
    model, name_to_task = create_model(
        number_of_tasks,
        cycle_time,
        task_times,
        predecessors,
    )
    solution, cost, bound, is_optimal, is_infeasible = solve(
        model,
        name_to_task,
        args.config,
        args.history,
        time_limit=args.time_out,
        seed=args.seed,
        threads=args.threads,
        initial_beam_size=args.initial_beam_size,
        parallel_type=args.parallel_type,
    )

    if is_infeasible:
        print("The problem is infeasible.")
    else:
        print("best bound: {}".format(bound))

        if cost is not None:
            print(solution)
            print("cost: {}".format(cost))

            if is_optimal:
                print("optimal cost: {}".format(cost))

            validation_result = read_salbp1.validate(
                number_of_tasks, cycle_time, task_times, predecessors, solution, cost
            )

            if validation_result:
                print("The solution is valid.")
            else:
                print("The solution is invalid.")
