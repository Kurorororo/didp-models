import os
import argparse
import math
import random

import networkx as nx


def generate_connected_graph(n, p):
    m = math.ceil(p * n * (n - 1) / 2)
    G = nx.gnm_random_graph(n, m)

    while not nx.is_connected(G):
        G = nx.gnm_random_graph(n, m)

    return G


def generate_weights(G, node_min, node_max, edge_min, edge_max):
    for v in G:
        G.nodes[v]["weight"] = random.randint(node_min, node_max)
    for u, v in G.edges:
        G.edges[u, v]["weight"] = random.randint(edge_min, edge_max)


def write_to_file(G, filename):
    with open(filename, "w") as f:
        f.write("{} {}\n".format(len(G), len(G.edges)))
        f.write(" ".join(str(G.nodes[u]["weight"]) for u in G) + "\n")

        for u in G:
            line = ""
            for v in G:
                if G.has_edge(u, v):
                    line += "{} ".format(G.edges[u, v]["weight"])
                else:
                    line += "0 "
            f.write(line + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=str)
    parser.add_argument("--seed", type=int, default=2022)
    parser.add_argument("--n-instances", type=int, default=5)
    parser.add_argument("--ns", type=int, nargs="+", default=[20, 30, 40])
    parser.add_argument(
        "--ps", type=float, nargs="+", default=[0.125, 0.25, 0.5, 0.75, 0.875]
    )
    parser.add_argument("--node-min", type=int, default=2)
    parser.add_argument("--node-max", type=int, default=10)
    parser.add_argument("--edge-min", type=int, default=1)
    parser.add_argument("--edge-max", type=int, default=4)
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    for n in args.ns:
        dirname = "random_n{}".format(n)
        dirpath = os.path.join(args.output_dir, dirname)
        os.makedirs(dirpath, exist_ok=True)
        for p in args.ps:
            for i in range(1, args.n_instances + 1):
                G = generate_connected_graph(n, p)
                generate_weights(
                    G, args.node_min, args.node_max, args.edge_min, args.edge_max
                )
                filename = "p{}_seed{}_{}".format(p, args.seed, i)
                filepath = os.path.join(dirpath, filename)
                write_to_file(G, filepath)
