# Single Machine Total Weighted Tardiness

- [Benchmark instances](http://people.brunel.ac.uk/~mastjjb/jeb/orlib/wtinfo.html)


```python3
python3 wt_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 wt_cp.py instance.txt --history history.csv --time-out 1800
```

## Kuroiwa and Beck 2023 Anytime and Journal Submission

```python3
python3 wt_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

- `-d`: didp-yaml binary
- `-c`: config YAML file

## Kuroiwa and Beck 2023 LNBS

```python3
python3 wt_didp.py instance.txt --config LNBS --history history.csv --time-out 1800
```

- `--config`: Solver name
