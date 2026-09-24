# MOSP

- Benchmark instances
  - https://doi.org/10.1371/journal.pone.0203076.s002
  - Large instances used in Kuroiwa and Beck 2023 LNBS
    - https://www.researchgate.net/publication/267864061_Minimization_of_Open_Stacks_Problem_MOSP_or_Minimization_of_Open_Orders_Problem_MOOP_Instances
    - https://www.researchgate.net/publication/324497787_Large_datasets_for_the_MOSP

```python3
python3 mosp_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 mosp_cp.py instance.txt --history history.csv --time-out 1800
```

## DIDPPy v0.11.1

Run from this directory with DIDPPy 0.11.1 installed (see the [root README](../README.md)).

```sh
python mosp_didp.py instance.txt --config CABS --time-out 1800 --history history.csv
```

`--config` accepts `CAASDy`, `CABS`, or `LNBS`. `--threads` and
`--initial-beam-size` configure CABS/LNBS; parallel search uses the default HD2
method. `--seed` controls LNBS randomization.

## YAML-DyPDL

```sh
python mosp_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs_max.yaml --memory-limit 8192
```

Use `../configs/caasdy_max.yaml` or `../configs/lnbs_max.yaml` to change the solver.
These configurations use the maximum-cost aggregation operator.
Omit `-d` to write the problem without solving it.

The original maximum-open-stacks formulation is retained. All three Python
solvers use the maximum-cost aggregation operator.
