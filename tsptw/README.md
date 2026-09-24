# TSPTW

[Benchmark instances](https://lopez-ibanez.eu/tsptw-instances)

The DIDP formulations use integer travel times and time windows. Use the integer
instances, or scale all travel times and windows consistently before solving.

```python3
python3 tsptw_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 tsptw_cp.py instance.txt --history history.csv --time-out 1800
```

## DIDPPy v0.11.1

Run from this directory with DIDPPy 0.11.1 installed (see the [root README](../README.md)).

```sh
python tsptw_didp.py instance.txt --config CABS --time-out 1800 --history history.csv
```

`--config` accepts `CAASDy`, `CABS`, or `LNBS`. `--threads` and
`--initial-beam-size` configure CABS/LNBS; parallel search uses the default HD2
method. `--seed` controls LNBS randomization.

## YAML-DyPDL

```sh
python tsptw_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

Use `../configs/caasdy.yaml` or `../configs/lnbs.yaml` to change the solver.
Omit `-d` to write the problem without solving it.

Both formulations use the return-to-depot cost in the base case. The sum of
minimum incoming/outgoing arc costs remains the default dual bound. Pass `--mst`
to either command to select an MST bound instead. Depot return deadlines are
checked at termination.

The YAML converter retains `--makespan`; it can be combined with `--mst`. The
makespan objective includes waiting time, while the default minimizes travel cost.
