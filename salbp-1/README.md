# SALBP-1

- [Benchmark instances](https://assembly-line-balancing.de/salbp/benchmark-data-sets-2013/)

```python3
python3 salbp1_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 salbp1_cp.py instance.txt --pack --history history.csv --time-out 1800
```

## DIDPPy v0.11.1

Run from this directory with DIDPPy 0.11.1 installed (see the [root README](../README.md)).

```sh
python salbp1_didp.py instance.txt --config CABS --time-out 1800 --history history.csv
```

`--config` accepts `CAASDy`, `CABS`, or `LNBS`. `--threads` and
`--initial-beam-size` configure CABS/LNBS; parallel search uses the default HD2
method. `--seed` controls LNBS randomization.

## YAML-DyPDL

```sh
python salbp1_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

Use `../configs/caasdy.yaml` or `../configs/lnbs.yaml` to change the solver.
Omit `-d` to write the problem without solving it.

The task-precedence constraints, station symmetry breaking, and existing dual
bounds are retained. The YAML converter retains its blind-bound option.
