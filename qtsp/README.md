# Quadratic traveling salesperson problem

The objective is the sum of costs of consecutive triples around a Hamiltonian cycle:

\[
\min_{\sigma}\sum_{t=0}^{n-1}c_{\sigma(t-1),\sigma(t),\sigma(t+1)}.
\]

Indices wrap around the cycle. Vertex 0 is fixed as the start. Input costs are
defined only for three distinct vertices; asymmetric nonnegative costs are supported.
The implementation is tested with DIDPPy 0.11.1 and Python 3.12.

## Original DIDP formulation

[`qtsp_didp.py`](qtsp_didp.py) implements the state `(U, i, j, f)` and transitions
from the [provided gist](https://gist.github.com/Kurorororo/dc33e2f92a93d4a7d0a5d3d7d67d9895):
unvisited vertices, previous vertex, current vertex, and first vertex after 0.
The first transition costs zero; each subsequent visit to `k` charges `c[i,j,k]`.
The terminal cost is **both** `c[i,j,0] + c[j,0,f]`.

The three lower bounds sum minimum incoming-, middle-, or outgoing-role costs.
The unmodified notebook and its revision are saved in [`reference/`](reference/).
Two corrections are documented explicitly:

* The notebook's code double-counts vertex 0 in its root bounds (`i=j=f=0`).
  We implement the **set unions in its mathematical equations**, counting 0 once.
  For a three-vertex instance with every valid triple costing 1, the notebook's
  coded bound is 4 although the optimum is 3; our bound is 3.
* Decimal-to-integer conversion uses decimal rounding and exact scaling. The
  notebook's `int(round(value, 2) * 100)` can truncate a binary floating-point
  artifact, for example converting 1.13 to 112 instead of 113.

## Instances and commands

Download the [benchmark instances and results](https://arxiv.org/src/1803.03681v1/anc/TestInstancesAndResults.rar)
accompanying [Staněk et al.](https://arxiv.org/abs/1803.03681).
The archive contains TSPLIB point sets, the conversion program, and published
bounds and results. Extract it outside the repository and pass an instance path
to the commands below. Both `.tsp` point sets and the gist's `.sqtsp` tensor format
are accepted.

`read_qtsp.py` follows the supplied `Tsp2Sqtsp.cpp` conversion:

* AngleTSP: `1000 * turning_angle`.
* AngleDistanceTSP: `100 * (40 * turning_angle + (d(i,j)+d(j,k))/2)`.

The converter's 16-significant-digit text serialization is reproduced before
rounding each triple to two decimal places and scaling to integers. The Python
reader was compared against compiled converter outputs for both types at sizes
5 and 10; every tensor entry matched. Published objective values round entire
unrounded tours, so small differences from sums of rounded triples are expected.
Reported solver proofs apply to the scaled integer instances.

Run from the repository root:

```sh
instance=/path/to/PointSet_15_1.tsp
.venv/bin/python qtsp/qtsp_didp.py "$instance" --kind angle --config CABS --time-out 30
.venv/bin/python qtsp/qtsp_to_didp.py "$instance" --kind angle -d didp-yaml -c configs/cabs.yaml
```

Both versions implement only the original `(U,i,j,f)` formulation and its three
role-minimum bounds. The first visit is free, and the non-zero base case includes
both closing triples. The Python solver optionally uses a deterministic insertion
tour as its initial incumbent (`--no-seed` disables it).

Python `--config` accepts `CAASDy`, `CABS`, or `LNBS`. Parallel CABS/LNBS uses
HD2; `--threads`, `--initial-beam-size`, and `--seed` configure the search.
`--json` saves the validated tour, objective, bound, and statistics; `--history`
saves improving incumbents. `--blind` disables the Python dual bounds.
The converter's `--output` selects the problem YAML filename.
