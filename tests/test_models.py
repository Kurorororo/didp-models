"""Exhaustive cross-checks of DIDPPy and YAML-DyPDL formulations."""

import importlib.util
import itertools
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

import didppy as dp

ROOT = Path(__file__).resolve().parents[1]


def load(folder, name):
    directory = ROOT / folder
    # Several independent model directories use the same reader module name.
    for source in directory.glob("*.py"):
        sys.modules.pop(source.stem, None)
    sys.path.insert(0, str(directory))
    try:
        spec = importlib.util.spec_from_file_location(
            f"test_{folder}_{name}", directory / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def yaml_model(folder, problem, domain="domain.yaml"):
    return dp.Model.load_from_str((ROOT / folder / domain).read_text(), problem)


def suffix_bounds(test, model):
    """Check every bound against the exact suffix value at every small state."""
    maximize = model.maximize
    infinity = -math.inf if maximize else math.inf
    choose = max if maximize else min
    transitions = model.get_transitions() + model.get_transitions(forced=True)

    def visit(state):
        if not model.check_state_constr(state):
            return infinity
        if model.is_base(state):
            value = model.eval_base_cost(state)
        else:
            value = infinity
            for transition in transitions:
                if transition.is_applicable(state, model):
                    successor = visit(transition.apply(state, model))
                    if successor != infinity:
                        value = choose(
                            value, transition.eval_cost(successor, state, model)
                        )
        for bound in model.dual_bounds:
            if maximize:
                test.assertGreaterEqual(bound.eval(state, model), value)
            else:
                test.assertLessEqual(bound.eval(state, model), value)
        return value

    return visit(model.target_state)


def optimum(model, solver="CAASDy", max_cost=False, threads=1):
    options = dict(
        quiet=True,
        time_limit=10,
        f_operator=dp.FOperator.Max if max_cost else dp.FOperator.Plus,
    )
    if solver == "CABS":
        search = dp.CABS(model, threads=threads, **options)
    elif solver == "LNBS":
        search = dp.LNBS(model, threads=threads, seed=2023, **options)
    else:
        search = dp.CAASDy(model, **options)
    solution = search.search()
    if solution.is_infeasible:
        return None
    if not solution.is_optimal:
        raise AssertionError("Tiny instance was not solved to optimality")
    return solution.cost


class ModelsTest(unittest.TestCase):
    def test_tsptw_default_and_mst(self):
        py = load("tsptw", "tsptw_didp")
        converter = load("tsptw", "tsptw_to_didp")
        for seed in range(8):
            rng = random.Random(seed)
            n = 5
            nodes = list(range(n))
            edges = {
                (i, j): rng.randrange(1, 12) for i in nodes for j in nodes if i != j
            }
            a = {i: rng.randrange(5) for i in nodes}
            b = {i: rng.randrange(12, 35) for i in nodes}
            feasible = []
            for order in itertools.permutations(nodes[1:]):
                time, cost, previous = max(0, a[0]), 0, 0
                for v in (*order, 0):
                    time = max(time + edges[previous, v], a[v])
                    cost += edges[previous, v]
                    if time > b[v]:
                        break
                    previous = v
                else:
                    feasible.append((cost, time - max(0, a[0])))
            expected = min((v[0] for v in feasible), default=None)
            problem = converter.create_didp(n, nodes, edges, a, b)
            for mst in (False, True):
                models = [
                    py.create_model(n, nodes, edges, a, b, mst=mst)[0],
                    yaml_model(
                        "tsptw", problem, "domain_mst.yaml" if mst else "domain.yaml"
                    ),
                ]
                for model in models:
                    self.assertEqual(optimum(model), expected)
                    self.assertEqual(
                        suffix_bounds(self, model),
                        expected if expected is not None else math.inf,
                    )
                    self.assertFalse(
                        any(t.name == "return" for t in model.get_transitions())
                    )
                makespan = yaml_model(
                    "tsptw",
                    problem,
                    "domain_makespan_mst.yaml" if mst else "domain_makespan.yaml",
                )
                self.assertEqual(
                    optimum(makespan), min((v[1] for v in feasible), default=None)
                )

    def test_cvrp_mst_with_nonmetric_edges(self):
        py = load("cvrp", "cvrp_didp")
        converter = load("cvrp", "cvrp_to_didp")
        for seed in range(8):
            rng = random.Random(seed + 100)
            n, capacity, k = 5, 5, 3
            nodes = list(range(1, n + 1))
            edges = {
                (i, j): rng.randrange(1, 20) for i in nodes for j in nodes if i != j
            }
            demand = {1: 0, **{i: rng.randrange(1, 4) for i in nodes[1:]}}
            expected = math.inf
            for order in itertools.permutations(nodes[1:]):
                for splits in itertools.product((False, True), repeat=n - 2):
                    if sum(splits) >= k:
                        continue
                    load_value, cost, previous = 0, 0, 1
                    for pos, v in enumerate(order):
                        if pos and splits[pos - 1]:
                            cost += edges[previous, 1]
                            load_value, previous = 0, 1
                        load_value += demand[v]
                        if load_value > capacity:
                            break
                        cost += edges[previous, v]
                        previous = v
                    else:
                        expected = min(expected, cost + edges[previous, 1])
            problem = converter.create_didp(n, nodes, edges, capacity, demand, k)
            for model in [
                py.create_model(n, nodes, edges, capacity, demand, k)[0],
                yaml_model("cvrp", problem),
            ]:
                self.assertEqual(optimum(model), expected)
                self.assertEqual(suffix_bounds(self, model), expected)
                self.assertFalse(
                    any(t.name == "return" for t in model.get_transitions())
                )

    def test_mpdtsp_sparse_graph_and_terminal_arc(self):
        py = load("m-pdtsp", "mpdtsp_didp")
        converter = load("m-pdtsp", "mpdtsp_to_didp")
        n, nodes, items = 4, [1, 2, 3, 4], [1]
        demand = {(v, 1): 2 if v == 2 else -2 if v == 3 else 0 for v in nodes}
        edges = {(1, 2): 3, (1, 3): 2, (2, 3): 4, (2, 4): 1, (3, 4): 5}
        for available, expected in [
            (edges, 12),
            ({e: w for e, w in edges.items() if e != (2, 3)}, None),
        ]:
            problem, infinity = converter.generate_problem(
                n, nodes, available, 2, items, demand
            )
            for model in [
                py.create_model(n, nodes, available, 2, items, demand)[0],
                yaml_model("m-pdtsp", problem),
            ]:
                self.assertEqual(optimum(model), expected)
                self.assertEqual(
                    suffix_bounds(self, model),
                    expected if expected is not None else math.inf,
                )
                self.assertFalse(
                    any(t.name == "finish" for t in model.get_transitions())
                )
                for solver in (dp.CAASDy, dp.CABS, dp.LNBS):
                    result = solver(
                        model, primal_bound=infinity, quiet=True, time_limit=5
                    ).search()
                    self.assertEqual(result.cost, expected)
                    self.assertEqual(result.is_infeasible, expected is None)
                    if expected is None:
                        self.assertGreaterEqual(
                            max(
                                h.eval(model.target_state, model)
                                for h in model.dual_bounds
                            ),
                            infinity,
                        )
                        self.assertEqual(result.expanded, 0)
            model, names, primal_bound = py.create_model(
                n, nodes, available, 2, items, demand
            )
            self.assertEqual(primal_bound, infinity)
            with tempfile.TemporaryDirectory() as directory:
                for solver in ("CAASDy", "CABS", "LNBS"):
                    result = py.solve(
                        model,
                        names,
                        solver,
                        Path(directory) / "history.csv",
                        primal_bound,
                        time_limit=5,
                    )
                    self.assertEqual(result[1], expected)
                    self.assertEqual(result[4], expected is None)
                    if expected is not None:
                        self.assertEqual(result[0], nodes)

    def test_mpdtsp_yaml_primal_bound(self):
        import yaml

        converter = load("m-pdtsp", "mpdtsp_to_didp")
        for original in (None, 5, 100):
            options = dict(time_limit=30)
            if original is not None:
                options["primal_bound"] = original
            config = dict(solver="dual_bound_cabs", config=options, dump_to="log.csv")
            result = yaml.safe_load(converter.create_solver_config(config, 20))
            self.assertEqual(
                result["config"]["primal_bound"],
                min(original, 20) if original is not None else 20,
            )
            self.assertEqual(result["config"]["time_limit"], 30)
            self.assertEqual(result["dump_to"], "log.csv")
            self.assertEqual(options.get("primal_bound"), original)

    def test_mdkp_fractional_bounds(self):
        py = load("mdkp", "mdkp_didp")
        converter = load("mdkp", "mdkp_to_didp")
        for seed in range(10):
            rng = random.Random(200 + seed)
            n, m = 6, 3
            profit = [rng.randrange(-2, 15) for _ in range(n)]
            weight = [[rng.randrange(0, 6) for _ in range(n)] for _ in range(m)]
            capacity = [rng.randrange(0, 10) for _ in range(m)]
            expected = max(
                sum(p * x for p, x in zip(profit, selected))
                for selected in itertools.product((0, 1), repeat=n)
                if all(
                    sum(w * x for w, x in zip(row, selected)) <= c
                    for row, c in zip(weight, capacity)
                )
            )
            for blind in (False, True):
                model = py.create_model(n, m, profit, weight, capacity, blind=blind)
                other = dp.Model.load_from_str(
                    converter.create_didp_domain(m, blind),
                    converter.create_didp_problem(n, m, profit, weight, capacity),
                )
                for model in [model, other]:
                    self.assertEqual(optimum(model), expected)
                    self.assertEqual(suffix_bounds(self, model), expected)

    def test_optw_filters_and_fractional_bounds(self):
        py = load("optw", "optw_didp")
        converter = load("optw", "optw_to_didp")
        for seed in range(10):
            rng = random.Random(300 + seed)
            n, vertices = 5, list(range(5))
            service = [0] + [rng.randrange(3) for _ in range(n - 1)]
            profits = [0] + [rng.randrange(1, 10) for _ in range(n - 1)]
            opening = [rng.randrange(3) for _ in vertices]
            closing = [25] + [rng.randrange(7, 20) for _ in vertices[1:]]
            distance = [
                [0 if i == j else rng.randrange(1, 8) for j in vertices]
                for i in vertices
            ]
            expected = 0
            for length in range(1, n):
                for order in itertools.permutations(vertices[1:], length):
                    current, time, value = 0, max(0, opening[0]), 0
                    for v in (*order, 0):
                        time = max(
                            time + service[current] + distance[current][v], opening[v]
                        )
                        if time > closing[v]:
                            break
                        value += profits[v]
                        current = v
                    else:
                        expected = max(expected, value)
            args = (vertices, service, profits, opening, closing, distance)
            for blind in (False, True):
                for model in [
                    py.create_model(*args, blind=blind)[0],
                    yaml_model(
                        "optw",
                        converter.create_didp(*args),
                        "domain_blind.yaml" if blind else "domain.yaml",
                    ),
                ]:
                    self.assertEqual(bool(model.dual_bounds), not blind)
                    self.assertEqual(optimum(model), expected)
                    self.assertEqual(suffix_bounds(self, model), expected)

    def test_optw_exhausted_capacity_with_positive_weights(self):
        py = load("optw", "optw_didp")
        converter = load("optw", "optw_to_didp")
        for deadline, expected in [(0, 0), (2, 7)]:
            args = (
                list(range(3)),
                [0, 0, 0],
                [0, 5, 7],
                [0, 0, 0],
                [deadline] * 3,
                [[0 if i == j else 1 for j in range(3)] for i in range(3)],
            )
            for model in [
                py.create_model(*args)[0],
                yaml_model("optw", converter.create_didp(*args)),
            ]:
                self.assertEqual(optimum(model), expected)
                self.assertEqual(suffix_bounds(self, model), expected)

    def test_graph_clear_dominance(self):
        py = load("graph-clear", "graph_clear_didp")
        converter = load("graph-clear", "graph_clear_to_didp")
        for seed in range(8):
            rng = random.Random(400 + seed)
            n = 5
            a = [rng.randrange(1, 6) for _ in range(n)]
            b = {(i, j): rng.randrange(0, 4) for i in range(n) for j in range(i + 1, n)}

            def edge(i, j):
                return b.get((min(i, j), max(i, j)), 0)

            def cost(order):
                clean, bound = set(), 0
                for v in order:
                    contaminated = set(range(n)) - clean - {v}
                    bound = max(
                        bound,
                        a[v]
                        + sum(edge(v, j) for j in range(n))
                        + sum(edge(i, j) for i in clean for j in contaminated),
                    )
                    clean.add(v)
                return bound

            expected = min(map(cost, itertools.permutations(range(n))))
            problem = converter.generate_problem(n, a, b)
            for model in [
                py.create_model(n, a, b)[0],
                yaml_model("graph-clear", problem),
            ]:
                self.assertEqual(optimum(model, max_cost=True), expected)
                if seed == 0:
                    for solver in ("CABS", "LNBS"):
                        self.assertEqual(
                            optimum(model, solver, max_cost=True, threads=2), expected
                        )

    def test_talent_subsumption_and_simplification(self):
        py = load("talent-scheduling", "talent_scheduling_didp")
        converter = load("talent-scheduling", "talent_scheduling_to_didp")
        reader = load("talent-scheduling", "read_talent_scheduling")
        for seed in range(12):
            rng = random.Random(500 + seed)
            n, m = 5, 4
            actors = [[rng.randrange(2) for _ in range(n)] for _ in range(m)]
            costs = [rng.randrange(1, 6) for _ in range(m)]
            durations = [rng.randrange(1, 5) for _ in range(n)]
            expected = min(
                reader.compute_solution_cost(p, actors, costs, durations)
                for p in itertools.permutations(range(n))
            )
            for simplified in (False, True):
                if simplified:
                    a, c, d, constant, mapping = reader.simplify(
                        actors, costs, durations
                    )
                else:
                    a, c, d, constant, mapping = (
                        actors,
                        costs,
                        durations,
                        0,
                        [[i] for i in range(n)],
                    )
                base = reader.compute_base_costs(a, c, d)
                problem = converter.generate_problem("tiny", a, c, d, base)
                for model in [
                    py.create_model(a, c, d, base)[0],
                    yaml_model("talent-scheduling", problem),
                ]:
                    self.assertEqual(optimum(model) + constant, expected)
                    solution = dp.CAASDy(model, quiet=True).search()
                    order = [
                        int(t.name.rsplit(" ", 1)[-1])
                        if " " in t.name and ":" not in t.name
                        else None
                        for t in solution.transitions
                    ]
                    if all(i is not None for i in order):
                        reconstructed, value = reader.reconstruct_solution(
                            order, solution.cost, constant, mapping
                        )
                        self.assertEqual(sorted(reconstructed), list(range(n)))
                        self.assertEqual(
                            reader.compute_solution_cost(
                                reconstructed, actors, costs, durations
                            ),
                            value,
                        )

    def test_bin_packing_cached_availability(self):
        py = load("bin-packing", "bpp_didp")
        converter = load("bin-packing", "bpp_to_didp")
        for seed in range(8):
            rng = random.Random(700 + seed)
            n, capacity = 6, 10
            weights = [rng.randrange(1, 11) for _ in range(n)]

            def pack(i, bins):
                if i == n:
                    return len(bins)
                result = pack(i + 1, bins + [weights[i]])
                for j, used in enumerate(bins):
                    if used + weights[i] <= capacity:
                        updated = bins.copy()
                        updated[j] += weights[i]
                        result = min(result, pack(i + 1, updated))
                return result

            expected = pack(0, [])
            problem = converter.generate_problem(n, capacity, weights)
            for model in [
                py.create_model(n, capacity, weights)[0],
                yaml_model("bin-packing", problem),
                yaml_model("bin-packing", problem, "domain_blind.yaml"),
            ]:
                self.assertEqual(optimum(model), expected)

    def test_weighted_tardiness_cached_time_and_precedence(self):
        py = load("wt", "wt_didp")
        converter = load("wt", "wt_to_didp")
        reader = load("wt", "read_single_machine_scheduling")
        for seed in range(8):
            rng = random.Random(800 + seed)
            n = 6
            times = [rng.randrange(1, 8) for _ in range(n)]
            due = [rng.randrange(1, 25) for _ in range(n)]
            weights = [rng.randrange(1, 8) for _ in range(n)]

            def cost(order):
                time, value = 0, 0
                for j in order:
                    time += times[j]
                    value += weights[j] * max(0, time - due[j])
                return value

            expected = min(map(cost, itertools.permutations(range(n))))
            before, _ = reader.extract_precedence_for_wt(times, due, weights)
            problem = converter.generate_problem(times, due, weights, before)
            for model in [
                py.create_model(times, due, weights, before)[0],
                py.create_model(times, due, weights, before, add_time_var=True)[0],
                yaml_model("wt", problem),
            ]:
                self.assertEqual(optimum(model), expected)

    def test_salbp_station_opening(self):
        py = load("salbp-1", "salbp1_didp")
        converter = load("salbp-1", "salbp1_to_didp")
        n, capacity = 5, 10
        times = {1: 6, 2: 4, 3: 5, 4: 3, 5: 2}
        before = {1: [], 2: [1], 3: [], 4: [2, 3], 5: [4]}
        problem = converter.generate_problem(n, capacity, times, before)
        for model in [
            py.create_model(n, capacity, times, before)[0],
            yaml_model("salbp-1", problem),
            yaml_model("salbp-1", problem, "domain_blind.yaml"),
        ]:
            for solver in ("CAASDy", "CABS", "LNBS"):
                self.assertEqual(optimum(model, solver, threads=2), 2)

    def test_mosp_maximum_cost_and_driver(self):
        py = load("mosp", "mosp_didp")
        converter = load("mosp", "mosp_to_didp")
        reader = load("mosp", "read_mosp")
        patterns = [[0, 1], [1, 2], [2, 3], [0, 3], [1, 3]]
        items = [[p for p, row in enumerate(patterns) if i in row] for i in range(4)]

        def cost(order):
            positions = {p: j for j, p in enumerate(order)}
            return max(
                sum(
                    min(positions[p] for p in row)
                    <= j
                    <= max(positions[p] for p in row)
                    for row in items
                )
                for j in range(len(patterns))
            )

        expected = min(map(cost, itertools.permutations(range(len(patterns)))))
        model, names = py.create_model(items, patterns)
        other = yaml_model("mosp", converter.create_didp("tiny", items, patterns))
        with tempfile.TemporaryDirectory() as directory:
            for solver in ("CAASDy", "CABS", "LNBS"):
                self.assertEqual(
                    optimum(other, solver, max_cost=True, threads=2), expected
                )
                result = py.solve(
                    model,
                    names,
                    items,
                    solver,
                    Path(directory) / "history.csv",
                    time_limit=5,
                    threads=2,
                )
                self.assertEqual(result[1], expected)
                self.assertTrue(result[3])
                self.assertTrue(reader.validate(items, patterns, result[0], result[1]))

    def test_dominance_lnbs_drivers(self):
        graph = load("graph-clear", "graph_clear_didp")
        talent = load("talent-scheduling", "talent_scheduling_didp")
        reader = load("talent-scheduling", "read_talent_scheduling")
        actors = [[1, 1, 0, 0, 1], [1, 0, 1, 1, 0], [0, 0, 0, 1, 1]]
        costs, durations = [3, 7, 2], [2, 1, 3, 2, 1]
        cases = [
            (
                graph,
                *graph.create_model(
                    4, [2, 3, 4, 5], {(0, 1): 2, (0, 3): 1, (1, 2): 3, (2, 3): 2}
                ),
                True,
            ),
            (
                talent,
                *talent.create_model(
                    actors,
                    costs,
                    durations,
                    reader.compute_base_costs(actors, costs, durations),
                ),
                False,
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for py, model, names, max_cost in cases:
                expected = optimum(model, max_cost=max_cost)
                for solver in ("CAASDy", "CABS", "LNBS"):
                    result = py.solve(
                        model,
                        names,
                        solver,
                        Path(directory) / "history.csv",
                        time_limit=5,
                        threads=2,
                    )
                    self.assertEqual(result[1], expected)
                    self.assertTrue(result[3])

    def test_qtsp_original_and_yaml(self):
        py = load("qtsp", "qtsp_didp")
        converter = load("qtsp", "qtsp_to_didp")
        reader = load("qtsp", "read_qtsp")
        for seed in range(8):
            rng = random.Random(600 + seed)
            n = 3 + seed % 4
            costs = [
                [
                    [
                        rng.randrange(1, 20) if len({i, j, k}) == 3 else 0
                        for k in range(n)
                    ]
                    for j in range(n)
                ]
                for i in range(n)
            ]
            expected = min(
                reader.tour_cost(costs, [0, *p, 0])
                for p in itertools.permutations(range(1, n))
            )
            for model in [
                py.create_model(n, costs)[0],
                yaml_model("qtsp", converter.create_didp(n, costs)),
            ]:
                self.assertEqual(optimum(model), expected)
                self.assertEqual(suffix_bounds(self, model), expected)
            if seed == 1:
                for solver in ("CAASDy", "CABS", "LNBS"):
                    result = py.solve(n, costs, solver, 5, threads=2)
                    self.assertTrue(result.is_optimal)
                    self.assertEqual(result.cost, expected)


if __name__ == "__main__":
    unittest.main()
