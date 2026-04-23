# MiniProject2DRTS

TSN-AVB worst-case delay analysis project for 02225 DRTS mini-project 2.

## WCRT Tool

`wcrt_tool` implements:
- CBS analytical WCRT via the eligible-interval method (Cao et al. 2016)
- Discrete-event CBS simulator (with optional SP mode)
- SP analytical WCRT via fixed-priority RTA
- Validation: confirms simulated WCRT ≤ analytical WCRT for every stream
- CSV outputs: per-stream WCRTs, per-link breakdowns, CBS-vs-SP comparison, BE starvation summary, credit traces

## Quick Setup

```bash
python3 -m pip install -r requirement.txt
```

## Verify Tests

```bash
python3 -m pytest -v wcrt_tool/tests/test_spec_pipeline.py
```

All 22 tests should pass, including exact-value checks for test_case_1 and test_case_3.

## Project Baseline (Mandatory Requirements)

The project specifies **idleSlope = sendSlope = 0.5** for simplicity.  The tool
defaults to this (`--policy fixed --alpha-a 0.5 --alpha-b 0.5`), so no extra flags are
needed.

Simplest run (point at one case directory):

```bash
python3 -m wcrt_tool tsn-test-cases/examples/test_case_1
```

This auto-loads `topology.json`, `streams.json`, `routes.json`, auto-detects
`WCRTs.csv` if present, and writes outputs to `output_data/test_case_1/`.

(`--input-dir tsn-test-cases/examples/test_case_1` is also supported as an alias.)

```bash
python3 -m wcrt_tool \
  --topology tsn-test-cases/examples/test_case_1/topology.json \
  --streams  tsn-test-cases/examples/test_case_1/streams.json \
  --routes   tsn-test-cases/examples/test_case_1/routes.json \
  --reference tsn-test-cases/examples/test_case_1/WCRTs.csv \
  --output   output_data/test_case_1
```

Key output files in `output_data/test_case_1/`:

| File | Contents |
|------|----------|
| `analytical_WCRTs.csv` | Per-stream CBS analytical WCRT, deadline, schedulable flag |
| `analytical_per_link_breakdown.csv` | SPI / HPI / LPI / C_i per link per stream |
| `simulation_results.csv` | Simulated WCRT, average RT, deadline misses |
| `validation_report.csv` | Analytical vs simulated ratio (should be ≥ 1) |

`analytical_WCRTs.csv` should match `WCRTs.csv` exactly (603.200, 632.800, 884.480, 808.000 μs).

## Optional Extension: CBS vs Strict Priority

Running with `--mode cbs` (the default) automatically runs a second SP pass and writes
additional comparison outputs:

| File | Contents |
|------|----------|
| `cbs_vs_sp_comparison.csv` | All streams (AVB + BE): CBS and SP analytical & simulated WCRTs side-by-side |
| `be_starvation_summary.csv` | BE streams only: miss rates under CBS vs SP; `Starved_under_SP=1` if SP causes misses while CBS does not |
| `credit_trace_<link>.csv` | Class-B CBS credit over time (for credit-evolution plots) |

The `be_starvation_summary.csv` directly demonstrates the key goal: the credit mechanism
preventing starvation of Best-Effort traffic under CBS while SP can starve it.

## Running All Three Test Cases

```bash
for TC in test_case_1 test_case_2 test_case_3; do
  python3 -m wcrt_tool tsn-test-cases/examples/$TC
done
```

## Richer idleSlope Assignment (Proportional Policy)

To use the utilisation-proportional slope assignment from Implementation_spec.md Section 5.3:

```bash
python3 -m wcrt_tool ... --policy proportional
```

This produces tighter slopes when link utilisations differ across streams.

## Note on test_case_2

`test_case_2` contains a 1 Gbps inter-switch link.  The reference `WCRTs.csv` for that
case was generated with a simplified tool that treated every link as 100 Mbps.  Our tool
correctly uses the actual per-link bandwidth (resulting in lower, tighter WCRTs on the
fast segment).  The test `test_analytical_wcrt_test_case_2_uses_actual_link_bandwidth`
documents this behaviour.
