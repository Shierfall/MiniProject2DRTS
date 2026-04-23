from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .analytical import build_alpha_plus_map, compute_cbs_wcrt, compute_sp_wcrt
from .parser import load_scenario
from .report import write_cbs_sp_comparison_report, write_reports
from .simulator import simulate


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AVB/CBS WCRT analytical + simulation tool")
    parser.add_argument(
        "case",
        nargs="?",
        help=(
            "Path to a case directory containing topology.json, streams.json, routes.json "
            "(and optionally WCRTs.csv)."
        ),
    )
    parser.add_argument(
        "--input-dir",
        help=(
            "Directory containing topology.json, streams.json, routes.json "
            "(and optionally WCRTs.csv). Alias of the positional case path."
        ),
    )
    parser.add_argument("--topology", help="Path to topology.json")
    parser.add_argument("--streams", help="Path to streams.json")
    parser.add_argument("--routes", help="Path to routes.json")
    parser.add_argument("--reference", help="Optional reference WCRTs.csv")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Output directory (default: output_data/<case-name> when using case/input-dir, else results)"
        ),
    )
    parser.add_argument("--duration", type=float, default=None, help="Simulation horizon in microseconds")
    parser.add_argument("--mode", choices=["cbs", "sp"], default="cbs", help="Scheduling mode")
    parser.add_argument(
        "--policy",
        choices=["proportional", "fixed"],
        default="fixed",
        help=(
            "idleSlope assignment policy. "
            "'fixed' (default): uses --alpha-a/--alpha-b uniformly on every link — "
            "matches the project baseline (idleSlope=sendSlope=0.5 for simplicity). "
            "'proportional': derives per-link slopes from stream utilisation per "
            "Implementation_spec.md Section 5.3."
        ),
    )
    parser.add_argument("--alpha-a", type=float, default=0.5, help="Class A idleSlope fraction (fixed policy) or fallback when AVB load is zero (proportional)")
    parser.add_argument("--alpha-b", type=float, default=0.5, help="Class B idleSlope fraction (fixed policy) or fallback when AVB load is zero (proportional)")
    args = parser.parse_args(argv)

    selected_case_paths = [p for p in (args.case, args.input_dir) if p]
    if len(selected_case_paths) > 1:
        parser.error("Use either positional case path or --input-dir, not both")

    using_case_dir = bool(selected_case_paths)
    if using_case_dir and any([args.topology, args.streams, args.routes]):
        parser.error("When using a case directory, do not also pass --topology/--streams/--routes")

    return args


def _resolve_input_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path | None, Path]:
    input_dir_arg = args.input_dir or args.case
    if input_dir_arg:
        input_dir = Path(input_dir_arg)
        if not input_dir.exists() or not input_dir.is_dir():
            raise SystemExit(f"Case directory not found: {input_dir}")

        topology = Path(args.topology) if args.topology else input_dir / "topology.json"
        streams = Path(args.streams) if args.streams else input_dir / "streams.json"
        routes = Path(args.routes) if args.routes else input_dir / "routes.json"

        if args.reference:
            reference = Path(args.reference)
        else:
            default_reference = input_dir / "WCRTs.csv"
            reference = default_reference if default_reference.exists() else None

        output = Path(args.output) if args.output else Path("output_data") / input_dir.name
    else:
        missing = [flag for flag, value in (("--topology", args.topology), ("--streams", args.streams), ("--routes", args.routes)) if not value]
        if missing:
            raise SystemExit(
                "Missing required input arguments. Use a positional case path or --input-dir for simple mode, "
                f"or provide all explicit paths: {', '.join(missing)}"
            )

        topology = Path(args.topology)
        streams = Path(args.streams)
        routes = Path(args.routes)
        reference = Path(args.reference) if args.reference else None
        output = Path(args.output) if args.output else Path("results")

    for label, path in (("topology", topology), ("streams", streams), ("routes", routes)):
        if not path.exists():
            raise SystemExit(f"Input file not found for {label}: {path}")

    if reference is not None and not reference.exists():
        raise SystemExit(f"Reference file not found: {reference}")

    return topology, streams, routes, reference, output


def main() -> None:
    args = _parse_args()
    topology_path, streams_path, routes_path, reference_path, output_dir = _resolve_input_paths(args)
    scenario = load_scenario(
        topology_path=topology_path,
        streams_path=streams_path,
        routes_path=routes_path,
    )

    alpha_plus = build_alpha_plus_map(
        scenario,
        policy=args.policy,
        alpha_a=args.alpha_a,
        alpha_b=args.alpha_b,
    )

    if args.mode == "cbs":
        analytical = compute_cbs_wcrt(scenario, alpha_plus)
    else:
        analytical = compute_sp_wcrt(scenario)

    simulation = simulate(
        scenario,
        alpha_plus_by_link=alpha_plus,
        duration_us=args.duration,
        mode=args.mode,
        capture_credit_trace=(args.mode == "cbs"),
    )

    write_reports(
        output_dir=output_dir,
        scenario=scenario,
        analytical=analytical,
        simulation=simulation,
        reference_path=reference_path,
    )

    if args.mode == "cbs":
        analytical_sp = compute_sp_wcrt(scenario)
        simulation_sp = simulate(scenario, alpha_plus_by_link=alpha_plus, duration_us=args.duration, mode="sp")
        write_cbs_sp_comparison_report(
            output_dir=output_dir,
            scenario=scenario,
            analytical_cbs=analytical,
            simulation_cbs=simulation,
            analytical_sp=analytical_sp,
            simulation_sp=simulation_sp,
        )

    print(f"Wrote reports to {output_dir.resolve()}")
    for warning in scenario.warnings:
        print(f"warning: {warning}")


if __name__ == "__main__":
    main()




