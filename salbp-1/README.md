# SALBP-1

- [Benchmark instances](https://assembly-line-balancing.de/salbp/benchmark-data-sets-2013/)

```python3
python3 salbp1_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 salbp1_cp.py instance.txt --pack --history history.csv --time-out 1800
```

## Kuroiwa and Beck 2023 CAASDy, Anytime, and Journal Submission

```python3
python3 salbp1_to_didp.py instance.txt -d didp-yaml -c ../configs/caasdy.yaml --memory-limit 8192
```

- `-d`: didp-yaml binary
- `-c`: config YAML file

### CABS/0

```python3
python3 salbp1_to_didp.py instance.txt --blind -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

## Kuroiwa and Beck 2023 LNBS

```python3
python3 salbp1_didp.py instance.txt --config LNBS --history history.csv --time-out 1800
```

- `--config`: Solver name
- `--threads`: Number of threads
- `--parallel-type`

## Kuroiwa and Beck 2024 Parallel

```python3
python3 salbp1_didp.py instance.txt --config CABS --initial-beam-size 32 --threads 4 --parallel-type 0 --history history.csv --time-out 300
```

- `--parallel-type`
  - `0`: HDBS2
  - `1`: HDBS1
  - `2`: SBS
