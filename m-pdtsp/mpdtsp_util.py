def compute_precedence(nodes, items, demand):
    precedence_edges = {}

    for i in nodes:
        if i != nodes[0] and i != nodes[-1]:
            precedence_edges[nodes[0], i] = 0
            precedence_edges[i, nodes[-1]] = 0
        for j in nodes:
            if i != j:
                for k in items:
                    if demand[i, k] > 0 and demand[j, k] < 0:
                        precedence_edges[i, j] = demand[i, k]
                        break

    return precedence_edges


def visit(i, nodes, precedence_edges, visited, result):
    if i not in visited:
        visited.add(i)
        for j in nodes:
            if (i, j) in precedence_edges:
                visit(j, nodes, precedence_edges, visited, result)
        result.append(i)


def topological_sort(nodes, precedence_edges):
    result = []
    visited = set()

    for i in nodes:
        visit(i, nodes, precedence_edges, visited, result)

    return list(reversed(result))


def compute_predecessors_and_successors(nodes, precedence_edges):
    sorted_nodes = topological_sort(nodes, precedence_edges)
    predecessors = {}

    for i in sorted_nodes:
        predecessors[i] = set()
        for j in sorted_nodes:
            if (j, i) in precedence_edges:
                predecessors[i].add(j)
                predecessors[i].update(predecessors[j])

    successors = {}

    for i in reversed(sorted_nodes):
        successors[i] = set()
        for j in reversed(sorted_nodes):
            if (i, j) in precedence_edges:
                successors[i].add(j)
                successors[i].update(successors[j])

    transitive_precedence_edges = {
        (i, j) for i in nodes for j in nodes if i in predecessors[j]
    }

    return predecessors, successors, transitive_precedence_edges


def compute_not_inferred_precedence(
    predecessors,
    successors,
    precedence_edges,
):
    not_inferred_precedence_edges = {b: d for b, d in precedence_edges.items()}

    for p, q in precedence_edges:
        intersection = successors[p] & predecessors[q]
        if len(intersection) > 0 and not_inferred_precedence_edges[p, q] == 0:
            del not_inferred_precedence_edges[p, q]
        else:
            for r in intersection:
                if (p, r) in not_inferred_precedence_edges and (
                    r,
                    q,
                ) in not_inferred_precedence_edges:
                    not_inferred_precedence_edges[
                        p, r
                    ] += not_inferred_precedence_edges[p, q]
                    not_inferred_precedence_edges[
                        r, q
                    ] += not_inferred_precedence_edges[p, q]
                    del not_inferred_precedence_edges[p, q]
                    break

    return not_inferred_precedence_edges


def check_edge(i, j, nodes, precedence_edges, capacity):
    return (
        sum(
            precedence_edges[p, q]
            for p in nodes
            for q in (i, j)
            if (p, q) in precedence_edges and p not in (i, j)
        )
        <= capacity
        and (
            sum(
                precedence_edges[b]
                for b in (
                    {(i, k) for k in nodes if (i, k) in precedence_edges}
                    | {(k, j) for k in nodes if (k, j) in precedence_edges}
                )
            )
            <= capacity
        )
        and (
            sum(
                precedence_edges[p, q]
                for p in (i, j)
                for q in nodes
                if (p, q) in precedence_edges and q not in (i, j)
            )
            <= capacity
        )
    )
