# MDKP

- [Benchmark instances](http://people.brunel.ac.uk/~mastjjb/jeb/orlib/mknapinfo.html)
  - Instances are separated into files.

```python3
python3 mdkp_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 mdkp_cp.py instance.txt --history history.csv --time-out 1800
```

## DIDPPy v0.11.1

Run from this directory with DIDPPy 0.11.1 installed (see the [root README](../README.md)).

```sh
python mdkp_didp.py instance.txt --config CABS --time-out 1800 --history history.csv
```

`--config` accepts `CAASDy`, `CABS`, or `LNBS`. `--threads` and
`--initial-beam-size` configure CABS/LNBS; parallel search uses the default HD2
method. `--seed` controls LNBS randomization.

## YAML-DyPDL

```sh
python mdkp_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

Use `../configs/caasdy.yaml` or `../configs/lnbs.yaml` to change the solver.
Omit `-d` to write the problem without solving it.

Both formulations use a fractional-knapsack upper bound for every capacity
dimension, as well as the sum of remaining positive profits. Remaining capacity
is a resource preferring larger values. Zero-weight items are included separately
in each bound. `--blind` disables the bounds and `--epsilon` controls the
nonnegative floating-point rounding tolerance (default `1e-6`).
