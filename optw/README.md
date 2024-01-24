# OPTW

- [Benchmark instances](https://www.mech.kuleuven.be/en/cib/op#section-6)

## Solomon Instances

```python3
python3 optw_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 optw_cp.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 optw_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```

## Cordeau Instances

```python3
python3 optw_mip.py instance.txt --round-to-second --history history.csv --time-out 1800
```

```python3
python3 optw_cp.py instance.txt --round-to-second --history history.csv --time-out 1800
```

```python3
python3 optw_to_didp.py instance.txt --round-to-second -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```
