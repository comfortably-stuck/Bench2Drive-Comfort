# Bench2Drive-Comfort

Comfort and standstill metrics for closed-loop [Bench2Drive](https://github.com/Thinklab-SJTU/Bench2Drive)
evaluation, as described in:

> **Comfortably Stuck: Evaluation Pitfalls in Bench2Drive's Closed-Loop Protocol**
> [arXiv:2610.21741](https://arxiv.org/abs/2610.21741)

The [project page source](https://github.com/comfortably-stuck/comfortably-stuck.github.io)
contains an overview of the findings and results.

Bench2Drive's official comfort metric has several implementation issues (a
sampling-rate mismatch, an undersized smoothing window, invalid yaw
processing) and, more fundamentally, rewards standing still: because routes
are scored in fixed 1-second segments rather than by distance traveled, a
vehicle that gets stuck early keeps accumulating trivially "comfortable"
stationary segments. This repository provides:

- **Traditional comfort** — Bench2Drive's original metric, unmodified (used
  here only for comparison, via the `Bench2Drive` submodule).
- **Fixed implementation** — the same metric with its implementation bugs
  corrected and its per-segment smoothing replaced with smoothing over the
  whole trajectory, removing segment-boundary artifacts.
- **Distance-based comfort (ours)** — the metric proposed in the paper:
  routes are split into 100 equal-distance segments instead of fixed-time
  ones, removing the incentive to stand still.
- **Standstill benchmark** — how much of a route the ego spends stationary,
  which the traditional comfort metric conflates with actual comfort.

See the [paper](https://arxiv.org/abs/2610.21741) for the full derivation and
discussion.

## Repository layout

```
comfort_metrics/        Metric implementations
  smoothing.py           Kinematic signal computation and comfort thresholds
  route_geometry.py      Projection of a trajectory onto a route polyline
  comfort.py             Traditional / fixed / distance-based comfort metrics
  standstill.py          Standstill benchmark
  results.py             Loading Bench2Drive evaluation output
scripts/
  evaluate_comfort.py    Per-route + aggregate comfort report for one run
  evaluate_standstill.py Per-route + aggregate standstill report for one run
  evaluate_all.py        All metrics above, for one or more runs
Bench2Drive/             Git submodule: unmodified upstream Bench2Drive
                         (or use an existing checkout via BENCH2DRIVE_ROOT)
```

## Setup

This repository extends Bench2Drive's evaluation tooling; it does not
replace it. Follow
[Bench2Drive's own setup instructions](https://github.com/Thinklab-SJTU/Bench2Drive#readme)
(CARLA, the leaderboard, and an agent) first, then add this repository for
the comfort and standstill metrics.

### Bench2Drive checkout

If you do not already have Bench2Drive, clone this repository with its
submodule:

```bash
git clone --recurse-submodules <this-repo-url>
cd Bench2Drive-Comfort
```

If you already have a Bench2Drive checkout, you can use it instead of
initializing this repository's submodule. Clone this repository normally (do
not add `--recurse-submodules`) and point `BENCH2DRIVE_ROOT` to the existing
checkout:

```bash
git clone <this-repo-url>
cd Bench2Drive-Comfort
export BENCH2DRIVE_ROOT=/absolute/path/to/Bench2Drive
```

The override is used for both the original comfort implementation and the
default route XML. If `BENCH2DRIVE_ROOT` is unset, the repository uses its
`Bench2Drive` submodule. You can also set the variable when running the
scripts if you have multiple Bench2Drive checkouts. This avoids replacing
the tracked submodule path with a symlink, which can make later Git submodule
updates confusing.

### Python environment

Run the metrics in your existing Bench2Drive Python environment when
available. Activate that environment, then install this repository's
dependencies there (only `numpy` and `scipy` are required):

```bash
conda activate <your-bench2drive-environment>
pip install -r requirements.txt
```

Only create a separate virtual environment if you do not have a usable
Bench2Drive environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Each script takes a Bench2Drive evaluation run directory: the directory
produced by the leaderboard, containing `results.json` (the filename set by
Bench2Drive's `run_leaderboard.sh`), or `simulation_results.json` (the
leaderboard evaluator's default filename), and one sub-folder per route with
that route's `metric_info.json`.

Comfort report (all three variants, per route and aggregated):

```bash
python scripts/evaluate_comfort.py <run_dir> -o comfort.csv
```

Standstill report:

```bash
python scripts/evaluate_standstill.py <run_dir> -o standstill.csv
```

All metrics for one or more runs (comfort, standstill, driving score, success
rate, efficiency — matching the paper's results table):

```bash
python scripts/evaluate_all.py <run_dir> [<run_dir> ...] -o results.csv
```

By default, route geometry for the distance-based metric is read from
`$BENCH2DRIVE_ROOT/leaderboard/data/bench2drive220.xml` when
`BENCH2DRIVE_ROOT` is set, or from
`Bench2Drive/leaderboard/data/bench2drive220.xml` otherwise (the 220-route
Bench2Drive benchmark). Pass a different file with `--route-xml` for other
route sets.

## Main results

Closed-loop results on the 220 Bench2Drive routes. UniAD and VAD use the
corrected protocol described in the paper (steering-overruling removed,
target-point sampling aligned with training); see the paper for details and
for results without those corrections.

| Method | Traditional Comfort | + Fixed Implementation | + Distance-Based (ours) | Time Spent Stationary (%) | Efficiency | Success Rate (%) | Driving Score |
|---|---|---|---|---|---|---|---|
| UniAD | 39.28 | 79.06 | 72.93 | 45.67 | 135.20 | 10.96 | 37.58 |
| VAD | 45.95 | 56.84 | 37.21 | 47.64 | 152.69 | 17.89 | 46.18 |
| SparseDriveV2 | 7.75 | 23.50 | 50.28 | 7.08 | 211.98 | 70.00 | 87.17 |
| TFv6 | 19.58 | 25.97 | 29.20 | 19.83 | 207.17 | 85.91 | 94.47 |
| Orion | 14.76 | 70.24 | 75.98 | 23.07 | 151.69 | 51.14 | 75.33 |
| SimLingo | 31.71 | 36.80 | 25.86 | 32.16 | 225.91 | 71.23 | 87.68 |
| CaRL | 22.81 | 61.36 | 71.84 | 24.76 | 177.60 | 57.27 | 81.82 |
| PDM-Lite | 22.77 | 32.57 | 35.82 | 20.43 | 250.80 | 91.19 | 96.59 |

Higher traditional/fixed/distance-based comfort and success rate are better;
lower time spent stationary is better among comparably capable models (a
model that never moves trivially scores 0% here).

## License and attribution

The code in this repository (`comfort_metrics/`, `scripts/`, and other files
outside `Bench2Drive/`) is licensed under the MIT License — see
[LICENSE](LICENSE).

`Bench2Drive/` is a git submodule that points, unmodified, at the official
[Bench2Drive repository](https://github.com/Thinklab-SJTU/Bench2Drive), which
is distributed under
[Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International
(CC BY-NC-ND 4.0)](https://creativecommons.org/licenses/by-nc-nd/4.0/). This
repository does not vendor, modify, or redistribute any Bench2Drive source
file; `traditional_comfort()` in `comfort_metrics/comfort.py` calls into the
selected Bench2Drive checkout's own, unmodified code at runtime rather than
reimplementing it.
Use of Bench2Drive itself (via the submodule) remains subject to its own
license, in particular its non-commercial and no-derivatives terms. Please
cite both this work and Bench2Drive if you use this repository:

```bibtex
@misc{aghajanzadeh2026comfortably,
  title  = {Comfortably Stuck: Evaluation Pitfalls in Bench2Drive's Closed-Loop Protocol},
  author = {Aghajanzadeh, Emad and Schwarzfischer, Thomas and Thoma, Moritz and
            Fasfous, Nael and Vemparala, Manoj Rohit and Mori, Pierpaolo and
            Mueller-Gritschneder, Daniel and Schlichtmann, Ulf},
  year   = {2026},
  eprint = {2610.21741},
  archivePrefix = {arXiv}
}

@inproceedings{jia2024bench2drive,
  title     = {Bench2Drive: Towards Multi-Ability Benchmarking of Closed-Loop End-To-End Autonomous Driving},
  author    = {Jia, Xiaosong and Yang, Zhenjie and Li, Qifeng and Zhang, Zhiyuan and Yan, Junchi},
  booktitle = {NeurIPS Datasets and Benchmarks Track},
  year      = {2024}
}
```
