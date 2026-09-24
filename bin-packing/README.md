# Bin Packing

- [Benchmark instances](https://site.unibo.it/operations-research/en/research/bpplib-a-bin-packing-problem-library)

```python3
python3 bpp_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 bpp_cp.py instance.txt --history history.csv --time-out 1800
```

## DIDPPy v0.11.1

Run from this directory with DIDPPy 0.11.1 installed (see the [root README](../README.md)).

```sh
python bpp_didp.py instance.txt --config CABS --time-out 1800 --history history.csv
```

`--config` accepts `CAASDy`, `CABS`, or `LNBS`. `--threads` and
`--initial-beam-size` configure CABS/LNBS; parallel search uses the default HD2
method. `--seed` controls LNBS randomization.

## YAML-DyPDL

```sh
python bpp_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

Use `../configs/caasdy.yaml` or `../configs/lnbs.yaml` to change the solver.
Omit `-d` to write the problem without solving it.

The model caches the all-items-unavailable condition as a Boolean state function.
The three packing bounds and item/bin symmetry breaking are retained.
