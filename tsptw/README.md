# TSPTW

[Benchmark instances](https://lopez-ibanez.eu/tsptw-instances)

```python3
python3 tsptw_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 tsptw_cp.py instance.txt --history history.csv --time-out 1800
```

## Kuroiwa and Beck 2023 CAASDy

```python3
python3 tsptw_to_didp.py instance.txt -d didp-yaml -c ../configs/caasdy.yaml --memory-limit 8192
```

- `-d`: didp-yaml binary
- `-c`: config YAML file

## Kuroiwa and Beck 2023 Anytime

```python3
python3 tsptw_to_didp.py instance.txt --use-bound -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

## Kuroiwa and Beck 2023 LNBS

```python3
python3 tsptw_didp.py instance.txt --config LNBS --history history.csv --time-out 1800
```

- `--config`: Solver name

## Kuroiwa and Beck 2024 Parallel

```python3
python3 tsptw_didp.py instance.txt --config CABS --initial-beam-size 32 --threads 4 --parallel-type 0 --history history.csv --time-out 300
```

- `--threads`: Number of threads
- `--parallel-type`
  - `0`: HDBS2
  - `1`: HDBS1
  - `2`: SBS

## Journal Submission

```python3
python3 tsptw_to_didp.py instance.txt --use-bound --non-zero-base-case -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

### CABS/0

```python3
python3 tsptw_to_didp.py instance.txt --non-zero-base-case -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

### TSPTW-M

```python3
python3 tsptw_to_didp.py instance.txt --makespan -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```
