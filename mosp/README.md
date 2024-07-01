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

## Kuroiwa and Beck 2023 CAASDy, Anytime, and Journal Submission

```python3
python3 mosp_to_didp.py instance.txt -d didp-yaml -c ../configs/caasdy.yaml --memory-limit 8192
```

- `-d`: didp-yaml binary
- `-c`: config YAML file

## Kuroiwa and Beck 2023 LNBS

```python3
python3 mosp_didp.py instance.txt --config LNBS --history history.csv --time-out 1800
```

- `--config`: Solver name

## Kuroiwa and Beck 2024 Parallel

```python3
python3 mosp_didp.py instance.txt --config CABS --initial-beam-size 32 --threads 4 --parallel-type 0 --history history.csv --time-out 300
```

- `--threads`: Number of threads
- `--parallel-type`
  - `0`: HDBS2
  - `1`: HDBS1
  - `2`: SBS
