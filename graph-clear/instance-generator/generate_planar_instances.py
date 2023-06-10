import os
import argparse
import random

import subprocess

import networkx as nx

import generate_instances


def generate_planner_graphs(n_instances, ns, command, output_path):
    n_to_graphs = {n: [] for n in ns}

    while any(len(graphs) < n_instances for graphs in n_to_graphs.values()):
        p = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
        )
        p.communicate()
        G = nx.Graph()
        with open(output_path) as f:
            line = f.readline().rstrip()
            line = f.readline().rstrip()
            while line != "0 0":
                nodes = line.split()
                G.add_edge(int(nodes[0]) - 1, int(nodes[1]) - 1)
                line = f.readline().rstrip()

        n = len(G)
        if n in ns and len(n_to_graphs[n]) < n_instances:
            print(n)
            n_to_graphs[n].append(G)

    return n_to_graphs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=str)
    parser.add_argument("--seed", type=int, default=2022)
    parser.add_argument("--n-instances", type=int, default=20)
    parser.add_argument("--ns", type=int, nargs="+", default=[20, 30, 40])
    parser.add_argument("--node-min", type=int, default=2)
    parser.add_argument("--node-max", type=int, default=10)
    parser.add_argument("--edge-min", type=int, default=1)
    parser.add_argument("--edge-max", type=int, default=4)
    parser.add_argument(
        "--output-path", type=str, default="BoltzmannPlanarGraphs/ListEdges.txt"
    )
    parser.add_argument(
        "--command",
        type=str,
        default="cd BoltzmannPlanarGraphs/build/classes && echo 1000"
        + " | java boltzmannplanargraphs.Main && cd ../../../",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    n_to_graphs = generate_planner_graphs(
        args.n_instances, args.ns, args.command, args.output_path
    )

    for n in args.ns:
        dirname = "planar_n{}".format(n)
        dirpath = os.path.join(args.output_dir, dirname)
        os.makedirs(dirpath, exist_ok=True)
        for i in range(args.n_instances):
            G = n_to_graphs[n][i]
            generate_instances.generate_weights(
                G, args.node_min, args.node_max, args.edge_min, args.edge_max
            )
            filename = "seed{}_{}".format(args.seed, i + 1)
            filepath = os.path.join(dirpath, filename)
            generate_instances.write_to_file(G, filepath)
