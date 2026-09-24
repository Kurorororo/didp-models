# CVRP

- [Benchmark instance-k4s](http://vrp.atd-lab.inf.puc-rio.br/index.php/en/)

The instance file must contain `k{#vehicles}` in its name.

```python3
python3 cvrp_mip.py instance-k4.txt --history history.csv --time-out 1800
```

```python3
python3 cvrp_cp.py instance-k4.txt --history history.csv --time-out 1800
```

## DIDPPy v0.11.1

Run from this directory with DIDPPy 0.11.1 installed (see the [root README](../README.md)).

```sh
python cvrp_didp.py instance-k4.txt --config CABS --time-out 1800 --history history.csv
```

`--config` accepts `CAASDy`, `CABS`, or `LNBS`. `--threads` and
`--initial-beam-size` configure CABS/LNBS; parallel search uses the default HD2
method. `--seed` controls LNBS randomization.

## YAML-DyPDL

```sh
python cvrp_to_didp.py instance-k4.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

Use `../configs/caasdy.yaml` or `../configs/lnbs.yaml` to change the solver.
Omit `-d` to write the problem without solving it.

The return-to-depot cost is evaluated in the base case. The default dual bound
is an MST on the unvisited customers and current location, plus a minimum return
cost. MST edge weights also allow travel via the depot, preserving validity for
nonmetric rounded distances. The YAML converter supports `--blind`.
