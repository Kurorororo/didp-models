# Talent Scheduling

- [Benchmark instances](https://people.eng.unimelb.edu.au/pstuckey/talent/)

```python3
python3 talent_scheduling_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 talent_scheduling_cp.py instance.txt --all-different --history history.csv --time-out 1800
```

## DIDPPy v0.11.1

Run from this directory with DIDPPy 0.11.1 installed (see the [root README](../README.md)).

```sh
python talent_scheduling_didp.py instance.txt --config CABS --time-out 1800 --history history.csv
```

`--config` accepts `CAASDy`, `CABS`, or `LNBS`. `--threads` and
`--initial-beam-size` configure CABS/LNBS; parallel search uses the default HD2
method. `--seed` controls LNBS randomization.

## YAML-DyPDL

```sh
python talent_scheduling_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

Use `../configs/caasdy.yaml` or `../configs/lnbs.yaml` to change the solver.
Omit `-d` to write the problem without solving it.

Both formulations use transition dominance for scene subsumption and cache
the actors already arrived and on standby. Actor-equivalent forced transitions,
single-scene actor elimination, duplicate-scene merging, and reconstruction to
the original scene sequence are retained. Repeated merging preserves earlier
scene blocks during reconstruction. The YAML converter retains `--blind`.
