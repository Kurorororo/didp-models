# Single Machine Total Weighted Tardiness

- [Benchmark instances](http://people.brunel.ac.uk/~mastjjb/jeb/orlib/wtinfo.html)


```python3
python3 wt_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 wt_cp.py instance.txt --history history.csv --time-out 1800
```

## DIDPPy v0.11.1

Run from this directory with DIDPPy 0.11.1 installed (see the [root README](../README.md)).

```sh
python wt_didp.py instance.txt --config CABS --time-out 1800 --history history.csv
```

`--config` accepts `CAASDy`, `CABS`, or `LNBS`. `--threads` and
`--initial-beam-size` configure CABS/LNBS; parallel search uses the default HD2
method. `--seed` controls LNBS randomization.

## YAML-DyPDL

```sh
python wt_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

Use `../configs/caasdy.yaml` or `../configs/lnbs.yaml` to change the solver.
Omit `-d` to write the problem without solving it.

By default, the sum of processing times of scheduled jobs is cached as a state
function. The Python model retains `--add-time-var` as an alternative explicit
time variable. Precedence extraction and the weighted-tardiness objective are
unchanged.
