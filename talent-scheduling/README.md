# Talent Scheduling

- [Benchmark instances](https://people.eng.unimelb.edu.au/pstuckey/talent/)

```python3
python3 talent_scheduling_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 talent_scheduling_cp.py instance.txt --all-different --history history.csv --time-out 1800
```

## Kuroiwa and Beck 2023 Anytime and Journal Submission

```python3
python3 talent_scheduling_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

- `-d`: didp-yaml binary
- `-c`: config YAML file

## CABS/0

```python3
python3 talent_scheduling_to_didp.py instance.txt --blind -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

## Kuroiwa and Beck 2023 LNBS

```python3
python3 talent_scheduling_didp.py instance.txt --config LNBS --history history.csv --time-out 1800
```

- `--config`: Solver name
