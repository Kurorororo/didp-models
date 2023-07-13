import os
import argparse
import random

import read_tsplib


def extract_direct_precedence(n, edges):
    predecessors = {}
    successors = {}

    for i in range(2, n):
        for j in range(2, n):
            if edges[i, j] == -1:
                if i not in predecessors:
                    predecessors[i] = set()

                if j not in successors:
                    successors[j] = set()

                predecessors[i].add(j)
                successors[j].add(i)

    direct_precedence = []

    for i in predecessors:
        for j in predecessors[i]:
            if successors[j].isdisjoint(predecessors[i]):
                direct_precedence.append((j, i))

    return sorted(direct_precedence)


def create_demand(nodes, precedence, max_demand):
    demand_dimension = len(precedence)
    demand = {i: [0] * demand_dimension for i in nodes}

    for k, (i, j) in enumerate(precedence):
        d = random.randint(1, max_demand)
        demand[i][k] = d
        demand[j][k] = -d

    return demand_dimension, demand


def generate_demand_lines(nodes, demand_dimension, demand):
    return ["DEMAND_DIMENSION: {}\n".format(demand_dimension), "DEMAND_SECTION\n"] + [
        "{}     ".format(i) + "    ".join(map(str, demand[i])) + "\n" for i in nodes
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sop_dir", help="Directory containing the SOP files")
    parser.add_argument("mpdtsp_dir", help="Directory to write the m-PDTSP files")
    parser.add_argument(
        "--capacity",
        "-q",
        type=int,
        nargs="+",
        default=[10],
    )
    parser.add_argument(
        "--max-demand",
        "-d",
        type=int,
        nargs="+",
        default=[1, 5],
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=2023,
    )
    args = parser.parse_args()

    random.seed(args.seed)

    for filename in os.listdir(args.sop_dir):
        problem_name, _ = os.path.splitext(filename)
        filepath = os.path.join(args.sop_dir, filename)
        n, nodes, edges, _ = read_tsplib.read_tsp(filepath)
        direct_precedence = extract_direct_precedence(n, edges)

        with open(filepath) as f:
            lines = f.readlines()

        for d in args.max_demand:
            for factor in args.capacity:
                q = d * factor
                demand_dimension, demand = create_demand(nodes, direct_precedence, d)
                capacity_lines = ["CAPACITY: {}\n".format(q)]
                demand_lines = generate_demand_lines(nodes, demand_dimension, demand)
                output_path = os.path.join(
                    args.mpdtsp_dir, "{}Q{}max{}.tsp".format(problem_name, q, d)
                )

                with open(output_path, "w") as f:
                    f.writelines(lines[:-1])
                    f.writelines(capacity_lines)
                    f.writelines(demand_lines)
                    f.writelines(lines[-1:])
