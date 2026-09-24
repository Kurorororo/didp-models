# OPTW

- [Benchmark instances](https://www.mech.kuleuven.be/en/cib/op#section-6)

## DIDPPy v0.11.1

```sh
python optw_didp.py instance.txt --config CABS --time-out 1800 --history history.csv
```

The model prefers states with more reachable customers and earlier service
start times. Every visit uses a set filter to remove unreachable customers.
Shortest travel times include service at the origin, keeping filtering sound
when rounded distances violate the triangle inequality. Two fractional-knapsack
upper bounds use minimum incoming and outgoing travel/service times as weights.
Customer weights are assumed positive, and each knapsack call uses `reachable`
directly. Depot opening times are supported. The sum of reachable profits is
omitted because it is implied by the two knapsack bounds.

OPTW may stop before visiting every customer. The finish transition returns to
the depot and naturally earns zero profit; distance-minimizing routing models
instead charge their return arc in the base case.

Only `CAASDy`, `CABS`, and `LNBS` are available. Parallel CABS/LNBS uses HD2;
`--threads`, `--initial-beam-size`, and `--seed` retain their usual meanings.
Both the Python model and YAML converter support `--blind`, `--round-to-second`,
and the nonnegative bound-rounding tolerance `--epsilon` (default `1e-6`).
The YAML model uses the same filtering and fractional-knapsack bounds.
Both bounds are defined in `domain.yaml`; `problem.yaml` contains only instance
data. The converter selects `domain_blind.yaml` when `--blind` is passed.

## Solomon Instances

```python3
python3 optw_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 optw_cp.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 optw_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

## Cordeau Instances

```python3
python3 optw_mip.py instance.txt --round-to-second --history history.csv --time-out 1800
```

```python3
python3 optw_cp.py instance.txt --round-to-second --history history.csv --time-out 1800
```

```python3
python3 optw_to_didp.py instance.txt --round-to-second -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```
