#!/usr/bin/env python3

import argparse
import os
import resource
import subprocess
import time

import read_mdkp
import yaml

start = time.perf_counter()


def get_limit_resource(time_limit, memory_limit):
    def limit_resources():
        if time_limit is not None:
            resource.setrlimit(resource.RLIMIT_CPU, (time_limit, time_limit + 5))

        if memory_limit is not None:
            resource.setrlimit(
                resource.RLIMIT_AS,
                (memory_limit * 1024 * 1024, memory_limit * 1024 * 1024),
            )

    return limit_resources


def create_didp_domain(m, blind=False):
    domain_file = """reduce: max
cost_type: integer
objects:
  - item
state_variables:
  - name: j
    type: element
    object: item"""

    for i in range(m):
        domain_file += """
  - name: r{}
    type: integer""".format(
            i
        )

    domain_file += """
tables:
  - name: profit
    type: integer
    args:
      - item
  - name: total_profit
    type: integer
    args:
      - item"""

    for i in range(m):
        domain_file += """
  - name: w{}
    type: integer
    args:
      - item""".format(
            i
        )

    for i in range(m):
        domain_file += """
  - name: max_efficiency{}
    type: continuous
    args:
      - item""".format(
            i
        )

    domain_file += """
transitions:
  - name: pack
    cost: (+ (profit j) cost)
    effect:
      j: (+ j 1)"""

    for i in range(m):
        domain_file += """
      r{}: (- r{} (w{} j))""".format(
            i, i, i
        )

    domain_file += """
    preconditions:"""

    for i in range(m):
        domain_file += """
      - (>= r{} (w{} j))""".format(
            i, i
        )

    domain_file += """
  - name: ignore
    cost: cost
    effect:
      j: (+ j 1)"""

    if not blind:
        domain_file += """
dual_bounds:
  - (total_profit j)"""

        for i in range(m):
            domain_file += """
  -     (floor (* (max_efficiency{} j) (max r{} 1)))""".format(
                i, i
            )

    domain_file += "\n"

    return domain_file


def create_didp_problem(n, m, profit, weight, capacity, epsilon=1e-6):
    problem_file = """object_numbers:
  item: {}
target:
  j: 0""".format(
        n + 1
    )

    for i in range(m):
        problem_file += """
  r{}: {}""".format(
            i, capacity[i]
        )

    problem_file += (
        """
table_values:
  n_items: {}
  profit: """.format(
            n
        )
        + "{"
        + ", ".join(["{}: {}".format(j, profit[j]) for j in range(n)])
        + "}"
    )

    total_profit = [sum(profit[j:]) for j in range(n)]
    problem_file += (
        """
  total_profit: {"""
        + ", ".join(["{}: {}".format(j, total_profit[j]) for j in range(n)])
        + "}"
    )

    for i in range(m):
        problem_file += (
            """
  w{}: """.format(
                i
            )
            + "{"
            + ", ".join(["{}: {}".format(j, weight[i][j]) for j in range(n)])
            + "}"
        )

    for i in range(m):
        efficiency = [
            profit[j] / weight[i][j] + epsilon if weight[i][j] > 0 else sum(profit[j:])
            for j in range(n)
        ]
        problem_file += (
            """
  max_efficiency{}: """.format(
                i
            )
            + "{"
            + ", ".join(["{}: {}".format(j, max(efficiency[j:])) for j in range(n)])
            + "}"
        )

    problem_file += """
base_cases:
  - - (= j {})""".format(
        n
    )

    problem_file += "\n"

    return problem_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("--didp-path", "-d", type=str)
    parser.add_argument("--config-path", "-c", type=str)
    parser.add_argument("--time-limit", default=None, type=int)
    parser.add_argument("--memory-limit", default=None, type=int)
    parser.add_argument("--epsilon", type=float, default=1e-6)
    parser.add_argument("--blind", action="store_true")
    args = parser.parse_args()

    n, m, profit, weight, capacity = read_mdkp.read_mdkp(args.input)

    domain_file = create_didp_domain(m, blind=args.blind)

    with open("domain.yaml", "w") as f:
        f.write(domain_file)

    problem_file = create_didp_problem(
        n,
        m,
        profit,
        weight,
        capacity,
        epsilon=args.epsilon,
    )

    with open("problem.yaml", "w") as f:
        f.write(problem_file)

    if args.didp_path is not None:
        fn = get_limit_resource(args.time_limit, args.memory_limit)
        print("Preprocessing time: {}s".format(time.perf_counter() - start))
        subprocess.run(
            [args.didp_path, "domain.yaml", "problem.yaml", args.config_path],
            preexec_fn=fn,
        )

    if os.path.exists("solution.yaml"):
        with open("solution.yaml") as f:
            result = yaml.safe_load(f)

        cost = result["cost"]
        solution = []

        for i, transition in enumerate(result["transitions"]):
            if transition["name"] == "pack":
                solution.append(i)

        print(solution)
        print("cost: {}".format(cost))

        validation_result = read_mdkp.validate_mdkp(
            m, profit, weight, capacity, solution, cost
        )

        if validation_result:
            print("The solution is valid.")
        else:
            print("The solution is invalid.")

    end = time.perf_counter()
    print("Execution time: {}s".format(end - start))
