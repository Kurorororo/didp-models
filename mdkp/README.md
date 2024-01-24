# MDKP

- [Benchmark instances](http://people.brunel.ac.uk/~mastjjb/jeb/orlib/mknapinfo.html)
  - Instances are separated into files.

```python3
python3 mdkp_mip.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 mdkp_cp.py instance.txt --history history.csv --time-out 1800
```

```python3
python3 mdkp_to_didp.py instance.txt -d didp-yaml -c ../configs/cabs.yaml --memory-limit 8192
```
