# Bin Packing

- [Benchmark instances](https://site.unibo.it/operations-research/en/research/bpplib-a-bin-packing-problem-library)

```python3
python3 bpp_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 bpp_cp.py instance.txt --history history.csv --time-out 1800
```

## Kuroiwa and Beck 2023 CAASDy, Anytime, and Journal Submission

```python3
python3 bpp_to_didp.py instance.txt -d didp-yaml -c ../configs/caasdy.yaml --memory-limit 8192
```

- `-d`: didp-yaml binary
- `-c`: config YAML file

### CABS/0

```python3
python3 bpp_to_didp.py instance.txt --blind -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

## Kuroiwa and Beck 2023 LNBS

```python3
python3 bpp_didp.py instance.txt --config LNBS --history history.csv --time-out 1800
```

- `--config`: Solver name

## Kuroiwa and Beck 2024 Parallel

```python3
python3 bpp_didp.py instance.txt --config CABS --initial-beam-size 32 --threads 4 --parallel-type 0 --history history.csv --time-out 300
```

- `--threads`: Number of threads
- `--parallel-type`
  - `0`: HDBS2
  - `1`: HDBS1
  - `2`: SBS
