# MiniProject2DRTS

TSN-AVB worst-case response time (WCRT) analysis tool for 02225 DRTS Mini-Project 2.

Implements the CBS eligible-interval method (Cao et al. 2016), a discrete-event simulator, and strict-priority RTA — all in one pipeline. Validates analytical bounds against simulation, generates comparison reports, and produces publication-ready figures.

---

## Features

| Feature | Description |
|---------|-------------|
| CBS analytical WCRT | Eligible-interval method per Cao et al. 2016; SPI/HPI/LPI/C_i breakdown per link |
| SP analytical WCRT | Fixed-priority response-time analysis for all streams |
| Discrete-event simulation | CBS or SP mode; captures per-stream WCRT, avg RT, deadline misses |
| Validation | Confirms `analytical ≥ simulated` for every stream; writes ratio report |
| CBS vs SP comparison | Side-by-side analytical + simulated WCRTs for every stream |
| BE starvation detection | Flags streams starved under SP but not under CBS |
| Credit traces | Class-B CBS credit over time per link (for plotting) |
| Figure generation | 7 matplotlib figures: breakdowns, scatter, credit trace, BE comparison, schedulability |
| idleSlope policies | `fixed` (α=0.5, project baseline) or `proportional` (utilisation-derived per spec §5.3) |

---

## Setup

```bash
python3 -m pip install -r requirement.txt
```

---

## Run Tests

```bash
python3 -m pytest -v wcrt_tool/tests/test_spec_pipeline.py
```

All 22 tests pass, including exact-value checks for `test_case_1` and `test_case_3`.

---

## Usage

### Simple mode — point at a case directory

```bash
python3 -m wcrt_tool tsn-test-cases/examples/test_case_1
```

Auto-loads `topology.json`, `streams.json`, `routes.json`; auto-detects `WCRTs.csv` if present; writes to `output_data/test_case_1/`.

### Explicit paths

```bash
python3 -m wcrt_tool \
  --topology  tsn-test-cases/examples/test_case_1/topology.json \
  --streams   tsn-test-cases/examples/test_case_1/streams.json \
  --routes    tsn-test-cases/examples/test_case_1/routes.json \
  --reference tsn-test-cases/examples/test_case_1/WCRTs.csv \
  --output    output_data/test_case_1
```

### All three test cases

```bash
for TC in test_case_1 test_case_2 test_case_3; do
  python3 -m wcrt_tool tsn-test-cases/examples/$TC
done
```

### Proportional idleSlope policy

```bash
python3 -m wcrt_tool tsn-test-cases/examples/test_case_1 --policy proportional
```

Derives per-link slopes from stream utilisation (Implementation_spec.md §5.3). Produces tighter bounds when link utilisations differ.

---

## CLI Reference

| Argument | Default | Description |
|----------|---------|-------------|
| `case` (positional) | — | Case directory with `topology.json`, `streams.json`, `routes.json` |
| `--input-dir` | — | Alias for positional case path |
| `--topology` | — | Explicit path to `topology.json` |
| `--streams` | — | Explicit path to `streams.json` |
| `--routes` | — | Explicit path to `routes.json` |
| `--reference` | auto-detect | Reference `WCRTs.csv` for comparison |
| `--output` | `output_data/<case>` | Output directory |
| `--mode` | `cbs` | Scheduling mode: `cbs` or `sp` |
| `--policy` | `fixed` | idleSlope policy: `fixed` or `proportional` |
| `--alpha-a` | `0.5` | Class A idleSlope fraction (fixed policy) |
| `--alpha-b` | `0.5` | Class B idleSlope fraction (fixed policy) |
| `--duration` | auto | Simulation horizon in microseconds |

---

## Output Files

All files written to `output_data/<case-name>/`:

| File | Contents |
|------|----------|
| `analytical_WCRTs.csv` | Per-stream CBS analytical WCRT, deadline, schedulable flag |
| `analytical_per_link_breakdown.csv` | SPI / HPI / LPI / C_i per link per stream (μs) |
| `simulation_results.csv` | Simulated WCRT, average RT, deadline miss count |
| `validation_report.csv` | Analytical/simulated ratio per stream (must be ≥ 1) |
| `cbs_vs_sp_comparison.csv` | CBS + SP analytical & simulated WCRTs side-by-side |
| `be_starvation_summary.csv` | BE streams: miss rates under CBS vs SP; `Starved_under_SP=1` if CBS protects BE |
| `credit_trace_<link>.csv` | Class-B CBS credit over time (one file per link) |

`analytical_WCRTs.csv` for `test_case_1` should match `WCRTs.csv` exactly: **603.200, 632.800, 884.480, 808.000 μs**.

---

## Figure Generation

Generates 7 figures from `output_data/` into `wcrt_tool/figures/`. Run all three test cases first.

```bash
python3 -m wcrt_tool.generate_figures
```

| Figure | File | Description |
|--------|------|-------------|
| 1 | `fig_wcrt_breakdown_tc1.png` | Stacked-bar WCRT breakdown (SPI/HPI/LPI/C_i) per stream — TC1 |
| 2 | `fig_analytical_vs_sim.png` | Analytical vs simulated WCRT across all three test cases |
| 3 | `fig_cbs_vs_sp.png` | CBS vs strict-priority side-by-side — TC1 |
| 4 | `fig_credit_trace.png` | Class-B CBS credit evolution on Link 2 — TC1, first 2.5 ms |
| 5 | `fig_bound_tightness.png` | Analytical/simulated ratio scatter across test cases (Class A & B) |
| 6 | `fig_be_comparison.png` | Best-effort mean WCRT: CBS vs SP across all test cases |
| 7 | `fig_schedulability.png` | Analytical WCRT vs deadline scatter — all three test cases |

---

## Input File Format

Three JSON files per test case (see `tsn-test-cases/docs/file_format_specs.v2.md` for full spec):

- **`topology.json`** — nodes (ES, switches) and unidirectional links with bandwidth/delay
- **`streams.json`** — traffic flows: priority class, frame size, period, deadline
- **`routes.json`** — pre-computed hop sequence per stream

---

## Project Baseline

Spec requires **idleSlope = sendSlope = 0.5**. Tool defaults: `--policy fixed --alpha-a 0.5 --alpha-b 0.5` — no extra flags needed.

### Note on test_case_2

`test_case_2` contains a 1 Gbps inter-switch link. The reference `WCRTs.csv` was generated with a tool that treated every link as 100 Mbps. This tool correctly uses actual per-link bandwidth, producing lower/tighter WCRTs on the fast segment. Test `test_analytical_wcrt_test_case_2_uses_actual_link_bandwidth` documents this.

---

## Project Structure

```
MiniProject2DRTS/
├── wcrt_tool/
│   ├── __main__.py          # CLI entry point
│   ├── analytical.py        # CBS + SP analytical WCRT
│   ├── simulator.py         # Discrete-event simulator
│   ├── parser.py            # JSON input loader
│   ├── model.py             # Data model (scenario, streams, links)
│   ├── report.py            # CSV report writers
│   ├── generate_figures.py  # Matplotlib figure generation (7 figures)
│   ├── figures/             # Generated figure output
│   └── tests/               # pytest test suite (22 tests)
├── tsn-test-cases/
│   └── examples/
│       ├── test_case_1/
│       ├── test_case_2/
│       └── test_case_3/
├── output_data/             # Generated — created on first run
├── requirement.txt
└── README.md
```
