from __future__ import annotations

from pathlib import Path

import pytest

from wcrt_tool.analytical import build_alpha_plus_map, compute_cbs_wcrt, compute_sp_wcrt
from wcrt_tool.parser import load_scenario
from wcrt_tool.simulator import simulate


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "tsn-test-cases" / "examples"


def _read_reference(path: Path) -> dict[int, float]:
    """Return {stream_id: wcrt_us} from a tab-separated WCRTs.csv."""
    values: dict[int, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        line = line.strip()
        if line:
            sid, wval = line.split("\t")
            values[int(sid)] = float(wval.replace(",", "."))
    return values


# ---------------------------------------------------------------------------
# Test case 1
# ---------------------------------------------------------------------------

def test_pipeline_test_case_1_reference_ids_present() -> None:
    """All AVB stream IDs in WCRTs.csv are covered by the analytical tool."""
    case_dir = EXAMPLES / "test_case_1"
    scenario = load_scenario(
        topology_path=case_dir / "topology.json",
        streams_path=case_dir / "streams.json",
        routes_path=case_dir / "routes.json",
    )

    alpha = build_alpha_plus_map(scenario, policy="proportional", alpha_a=0.5, alpha_b=0.5)
    analytical = compute_cbs_wcrt(scenario, alpha)
    simulation = simulate(scenario, alpha_plus_by_link=alpha, duration_us=20_000)
    analytical_sp = compute_sp_wcrt(scenario)
    simulation_sp = simulate(scenario, alpha_plus_by_link=alpha, duration_us=20_000, mode="sp")

    refs = set(_read_reference(case_dir / "WCRTs.csv").keys())
    assert refs.issubset(set(analytical.keys()))

    for stream_id in refs:
        assert analytical[stream_id].total_wcrt_us > 0.0
        assert simulation.max_response_time(stream_id) > 0.0
        assert analytical_sp[stream_id].total_wcrt_us > 0.0
        assert simulation_sp.max_response_time(stream_id) > 0.0


@pytest.mark.parametrize("stream_id,expected_us", [
    (0, 603.2),
    (1, 603.2),
    (2, 632.8),
    (3, 632.8),
    (4, 884.48),
    (5, 884.48),
    (6, 808.0),
    (7, 808.0),
])
def test_analytical_wcrt_test_case_1_fixed_slopes(stream_id: int, expected_us: float) -> None:
    """Analytical WCRTs match the reference file exactly when using fixed alpha=0.5 slopes.

    The reference WCRTs.csv was generated with idleSlope=sendSlope=0.5 for both classes.
    All links in test_case_1 are 100 Mbps so there is no bandwidth ambiguity.
    """
    case_dir = EXAMPLES / "test_case_1"
    scenario = load_scenario(
        topology_path=case_dir / "topology.json",
        streams_path=case_dir / "streams.json",
        routes_path=case_dir / "routes.json",
    )
    alpha = build_alpha_plus_map(scenario, policy="fixed", alpha_a=0.5, alpha_b=0.5)
    analytical = compute_cbs_wcrt(scenario, alpha)
    assert abs(analytical[stream_id].total_wcrt_us - expected_us) < 0.01


def test_simulator_upper_bounds_analytical_test_case_1() -> None:
    """Simulated WCRT must not exceed the analytical WCRT (analysis is a proven upper bound)."""
    case_dir = EXAMPLES / "test_case_1"
    scenario = load_scenario(
        topology_path=case_dir / "topology.json",
        streams_path=case_dir / "streams.json",
        routes_path=case_dir / "routes.json",
    )
    alpha = build_alpha_plus_map(scenario, policy="fixed", alpha_a=0.5, alpha_b=0.5)
    analytical = compute_cbs_wcrt(scenario, alpha)
    simulation = simulate(scenario, alpha_plus_by_link=alpha, duration_us=100_000)

    for stream_id, result in analytical.items():
        sim_wcrt = simulation.max_response_time(stream_id)
        assert sim_wcrt <= result.total_wcrt_us + 0.01, (
            f"Stream {stream_id}: simulated {sim_wcrt:.3f} > analytical {result.total_wcrt_us:.3f}"
        )


# ---------------------------------------------------------------------------
# Test case 2
# ---------------------------------------------------------------------------

def test_pipeline_test_case_2_runs() -> None:
    case_dir = EXAMPLES / "test_case_2"
    scenario = load_scenario(
        topology_path=case_dir / "topology.json",
        streams_path=case_dir / "streams.json",
        routes_path=case_dir / "routes.json",
    )
    alpha = build_alpha_plus_map(scenario, policy="proportional", alpha_a=0.5, alpha_b=0.5)
    analytical = compute_cbs_wcrt(scenario, alpha)
    simulation = simulate(scenario, alpha_plus_by_link=alpha, duration_us=20_000)

    assert len(analytical) >= 8
    assert all(simulation.response_times_by_stream[stream.stream_id] for stream in scenario.streams)


def test_analytical_wcrt_test_case_2_matches_reference() -> None:
    """Analytical WCRTs match reference exactly; all links are 100 Mbps (default_bandwidth_mbps)."""
    case_dir = EXAMPLES / "test_case_2"
    scenario = load_scenario(
        topology_path=case_dir / "topology.json",
        streams_path=case_dir / "streams.json",
        routes_path=case_dir / "routes.json",
    )
    alpha = build_alpha_plus_map(scenario, policy="fixed", alpha_a=0.5, alpha_b=0.5)
    analytical = compute_cbs_wcrt(scenario, alpha)

    ref = _read_reference(case_dir / "WCRTs.csv")
    for stream_id, ref_wcrt in ref.items():
        our_wcrt = analytical[stream_id].total_wcrt_us
        assert abs(our_wcrt - ref_wcrt) < 0.01, (
            f"Stream {stream_id}: computed {our_wcrt:.3f} != reference {ref_wcrt:.3f}"
        )


# ---------------------------------------------------------------------------
# Test case 3
# ---------------------------------------------------------------------------

def test_pipeline_test_case_3_runs() -> None:
    case_dir = EXAMPLES / "test_case_3"
    scenario = load_scenario(
        topology_path=case_dir / "topology.json",
        streams_path=case_dir / "streams.json",
        routes_path=case_dir / "routes.json",
    )
    alpha = build_alpha_plus_map(scenario, policy="proportional", alpha_a=0.5, alpha_b=0.5)
    analytical = compute_cbs_wcrt(scenario, alpha)
    simulation = simulate(scenario, alpha_plus_by_link=alpha, duration_us=20_000)

    assert len(analytical) >= 8
    assert all(simulation.response_times_by_stream[stream.stream_id] for stream in scenario.streams)


@pytest.mark.parametrize("stream_id,expected_us", [
    (0, 601.6),
    (1, 601.6),
    (2, 574.56),
    (3, 574.56),
    (4, 919.2),
    (5, 919.2),
    (6, 957.12),
    (7, 957.12),
])
def test_analytical_wcrt_test_case_3_fixed_slopes(stream_id: int, expected_us: float) -> None:
    """Analytical WCRTs match the reference file exactly when using fixed alpha=0.5 slopes.

    All links in test_case_3 are 100 Mbps so there is no bandwidth ambiguity.
    """
    case_dir = EXAMPLES / "test_case_3"
    scenario = load_scenario(
        topology_path=case_dir / "topology.json",
        streams_path=case_dir / "streams.json",
        routes_path=case_dir / "routes.json",
    )
    alpha = build_alpha_plus_map(scenario, policy="fixed", alpha_a=0.5, alpha_b=0.5)
    analytical = compute_cbs_wcrt(scenario, alpha)
    assert abs(analytical[stream_id].total_wcrt_us - expected_us) < 0.01


def test_simulator_upper_bounds_analytical_test_case_3() -> None:
    """Simulated WCRT must not exceed the analytical WCRT for test_case_3."""
    case_dir = EXAMPLES / "test_case_3"
    scenario = load_scenario(
        topology_path=case_dir / "topology.json",
        streams_path=case_dir / "streams.json",
        routes_path=case_dir / "routes.json",
    )
    alpha = build_alpha_plus_map(scenario, policy="fixed", alpha_a=0.5, alpha_b=0.5)
    analytical = compute_cbs_wcrt(scenario, alpha)
    simulation = simulate(scenario, alpha_plus_by_link=alpha, duration_us=100_000)

    for stream_id, result in analytical.items():
        sim_wcrt = simulation.max_response_time(stream_id)
        assert sim_wcrt <= result.total_wcrt_us + 0.01, (
            f"Stream {stream_id}: simulated {sim_wcrt:.3f} > analytical {result.total_wcrt_us:.3f}"
        )
