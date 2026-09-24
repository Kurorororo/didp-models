# Models for the DIDP Papers

This repository contains DIDPPy and YAML-DyPDL models updated for **v0.11.1**,
alongside MIP and CP models. The tagged historical versions preserve the models
used in past papers; current code and command-line options may differ.

## Setup and validation

```sh
python -m venv .venv
.venv/bin/python -m pip install didppy==0.11.1 'PyYAML>=6.0' ruff==0.16.8
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m unittest discover -s tests -v
```

Use the matching v0.11.1 `didp-yaml` binary for YAML-DyPDL. See the
[DIDPPy documentation](https://didppy.readthedocs.io/en/v0.11.1/),
[Python examples](https://github.com/domain-independent-dp/didp-rs/tree/main/didppy/examples),
and [YAML examples](https://github.com/domain-independent-dp/didp-rs/tree/main/didp-yaml/examples).
MIP and CP scripts require their respective solver packages separately.

YAML configurations are in [`configs`](configs). Their time limits
are configured in the YAML files. Each problem README retains the instance
sources and describes its current commands.
Graph-clear and MOSP require the `*_max.yaml` configurations, which use `max`
to combine prefix costs and suffix bounds.

## Papers

The repository originated with the models used in the following papers.

- Ryo Kuroiwa and J. Christopher Beck, [Domain-Independent Dynamic Programming](https://doi.org/10.1016/j.artint.2026.104506), *Artificial Intelligence*, 2026.
    - Ryo Kuroiwa and J. Christopher Beck, [Domain-Independent Dynamic Programming: Generic State Space Search for Combinatorial Optimization](https://doi.org/10.1609/icaps.v33i1.27200), *International Conference on Automated Planning and Scheduling (ICAPS)*, 2023. [supplement](https://tidel.mie.utoronto.ca/pubs/Appendix_CAASDy_ICAPS23.pdf)
    - Ryo Kuroiwa and J. Christopher Beck, [Solving Domain-Independent Dynamic Programming Problems with Anytime Heuristic Search](https://doi.org/10.1609/icaps.v33i1.27201), *International Conference on Automated Planning and Scheduling (ICAPS)*, 2023. [supplement](https://tidel.mie.utoronto.ca/pubs/Appendix_Anytime_ICAPS23.pdf)
- Ryo Kuroiwa and J. Christopher Beck, [Large Neighborhood Beam Search for Domain-Independent Dynamic Programming](https://doi.org/10.4230/LIPIcs.CP.2023.23), *International Conference on Principles and Practice of Constraint Programming (CP)*, 2023.
- Ryo Kuroiwa and J. Christopher Beck, [Parallel Beam Search Algorithms for Domain-Independent Dynamic Programming](https://doi.org/10.1609/aaai.v38i18.30062), *Annual AAAI Conference on Artificial Intelligence (AAAI)*, 2024. [supplement](https://tidel.mie.utoronto.ca/pubs/Appendix_Parallel_AAAI24.pdf)
- Yuxiao Chen, Anubhav Singh, Ryo Kuroiwa, and J. Christopher Beck, [New Exact Methods for Solving Quadratic Traveling Salesman Problem](https://doi.org/10.1609/icaps.v35i1.36134), *International Conference on Automated Planning and Scheduling (ICAPS)*, 2025.

In addition, PDDL models for some problems and Picat models are provided.

## More Models

The discrete-optimization repository maintained by airbus also implement DP models for multiple problems using DIDPPy: https://github.com/airbus/discrete-optimization
