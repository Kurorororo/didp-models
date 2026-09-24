"""Readers for SQ-TSP tensors and the supplied TSPLIB point sets."""

import math
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path


def scaled_cost(value, decimals=2):
    if not 0 <= decimals <= 6:
        raise ValueError("decimals must be between 0 and 6")
    value = Decimal(str(value))
    if not value.is_finite() or value < 0:
        raise ValueError("QTSP costs must be finite and nonnegative")
    return int((value * 10**decimals).to_integral_value(rounding=ROUND_HALF_EVEN))


def read_qtsp(filename, n_decimal_places=2):
    """Read n followed by the n(n-1)(n-2) ordered distinct-triple costs."""
    tokens = Path(filename).read_text().split()
    n = int(tokens[0])
    if n < 3 or len(tokens) != 1 + n * (n - 1) * (n - 2):
        raise ValueError("Invalid SQ-TSP dimension or number of costs")
    values = iter(tokens[1:])
    costs = [[[0] * n for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if len({i, j, k}) == 3:
                    costs[i][j][k] = scaled_cost(next(values), n_decimal_places)
    return n, costs


def read_points(filename):
    metadata, points = {}, []
    in_coordinates = False
    for line in Path(filename).read_text().splitlines():
        line = line.strip()
        if line == "NODE_COORD_SECTION":
            in_coordinates = True
        elif line == "EOF":
            break
        elif in_coordinates and line:
            index, x, y = line.split()
            if int(index) != len(points) + 1:
                raise ValueError("Point indices must be consecutive from 1")
            points.append((float(x), float(y)))
        elif ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    if metadata.get("EDGE_WEIGHT_TYPE") != "EUC_2D":
        raise ValueError("Only EUC_2D point sets are supported")
    if int(metadata.get("DIMENSION", 0)) != len(points) or len(points) < 3:
        raise ValueError("Invalid TSPLIB dimension")
    if not all(math.isfinite(x) and math.isfinite(y) for x, y in points):
        raise ValueError("Coordinates must be finite")
    if len(set(points)) != len(points):
        raise ValueError("Coincident points have undefined turning angles")
    return points


def point_costs(points, kind="angle", decimals=2):
    """Match the supplied Tsp2Sqtsp.cpp formulas and 16-digit serialization.

    AngleTSP: 1000 * angle; AngleDistanceTSP: 100 * (40 * angle
    + (distance(i,j) + distance(j,k))/2). The angle is the turning angle,
    not the internal angle. Reversal symmetry is preserved explicitly.
    """
    if kind not in ("angle", "angle-distance"):
        raise ValueError("Unknown instance kind")
    n = len(points)
    distances = [
        [math.sqrt((x - u) ** 2 + (y - v) ** 2) for u, v in points] for x, y in points
    ]
    costs = [[[0] * n for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(i + 1, n):
                if j in (i, k):
                    continue
                x, y = points[j][0] - points[i][0], points[j][1] - points[i][1]
                u, v = points[k][0] - points[j][0], points[k][1] - points[j][1]
                cosine = (x * u + y * v) / distances[i][j] / distances[j][k]
                angle = math.acos(max(-1.0, min(1.0, cosine)))
                value = (
                    1000 * angle
                    if kind == "angle"
                    else 100
                    * (40 * angle + 0.5 * distances[i][j] + 0.5 * distances[j][k])
                )
                cost = scaled_cost(format(value, ".16g"), decimals)
                costs[i][j][k] = costs[k][j][i] = cost
    return costs


def load_instance(filename, kind="angle", decimals=2):
    if Path(filename).suffix.lower() == ".tsp":
        points = read_points(filename)
        return len(points), point_costs(points, kind, decimals)
    return read_qtsp(filename, decimals)


def tour_cost(costs, tour):
    """Evaluate a closed walk independently of the DIDP transitions."""
    if len(tour) < 4 or tour[0] != 0 or tour[-1] != 0:
        raise ValueError("A tour must start/end at 0 and have at least three vertices")
    cycle = tour[:-1]
    if any(v < 0 or v >= len(costs) for v in cycle) or 0 in cycle[1:]:
        raise ValueError("Invalid vertex or intermediate depot visit")
    total = 0
    for t, j in enumerate(cycle):
        i, k = cycle[t - 1], cycle[(t + 1) % len(cycle)]
        if len({i, j, k}) != 3:
            raise ValueError("Costs require three distinct consecutive vertices")
        total += costs[i][j][k]
    return total


def validate_tour(costs, tour, objective):
    if tour is None or len(tour) != len(costs) + 1:
        return False
    if sorted(tour[:-1]) != list(range(len(costs))):
        return False
    try:
        return tour_cost(costs, tour) == objective
    except (ValueError, TypeError):
        return False


def insertion_tour(costs):
    """Construct a Hamiltonian tour by cheapest insertion.

    Recompute insertion deltas for quadratic costs; ordinary TSP edge deltas
    are not valid here. The result is feasible without any metric assumption.
    """
    n = len(costs)
    cycle = [0, 1, 2]
    missing = set(range(n)) - set(cycle)
    while missing:
        options = []
        for position, b in enumerate(cycle):
            a = cycle[position - 1]
            c, d = (
                cycle[(position + 1) % len(cycle)],
                cycle[(position + 2) % len(cycle)],
            )
            for k in missing:
                delta = (
                    costs[a][b][k]
                    + costs[b][k][c]
                    + costs[k][c][d]
                    - costs[a][b][c]
                    - costs[b][c][d]
                )
                options.append((delta, k, position))
        _, k, position = min(options)
        cycle.insert(position + 1, k)
        missing.remove(k)
    tour = cycle + [0]
    return tour, tour_cost(costs, tour)
