from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict

from .analytical import AnalyticalResult
from .model import AVB_CLASSES, Scenario
from .simulator import SimulationResult


def _read_reference(reference_path: str | None) -> Dict[int, float]:
    if not reference_path:
        return {}

    values: Dict[int, float] = {}
    with Path(reference_path).open("r", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader, None)
        for row in reader:
            if not row:
                continue
            stream_id = int(row[0])
            value = float(row[1].replace(",", "."))
            values[stream_id] = value
    return values


def write_reports(
    output_dir: str | Path,
    scenario: Scenario,
    analytical: Dict[int, AnalyticalResult],
    simulation: SimulationResult,
    reference_path: str | None = None,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    analytical_csv = output_path / "analytical_WCRTs.csv"
    with analytical_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ID", "Priority", "Deadline_us", "Analytical_WCRT_us", "Schedulable"])
        for stream_id, result in sorted(analytical.items()):
            writer.writerow(
                [
                    stream_id,
                    result.stream.priority,
                    f"{result.stream.deadline_us:.3f}",
                    f"{result.total_wcrt_us:.3f}",
                    int(result.total_wcrt_us <= result.stream.deadline_us),
                ]
            )

    breakdown_csv = output_path / "analytical_per_link_breakdown.csv"
    with breakdown_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ID", "Link", "SPI_us", "HPI_us", "LPI_us", "C_i_us", "WCRT_link_us"])
        for stream_id, result in sorted(analytical.items()):
            for entry in result.per_link:
                writer.writerow(
                    [
                        stream_id,
                        entry.link_id,
                        f"{entry.spi_us:.3f}",
                        f"{entry.hpi_us:.3f}",
                        f"{entry.lpi_us:.3f}",
                        f"{entry.c_i_us:.3f}",
                        f"{entry.total_us:.3f}",
                    ]
                )

    simulation_csv = output_path / "simulation_results.csv"
    with simulation_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ID", "Samples", "Average_RT_us", "Simulated_WCRT_us", "Deadline_Misses"])
        for stream in sorted(scenario.streams, key=lambda stream: stream.stream_id):
            samples = simulation.response_times_by_stream.get(stream.stream_id, [])
            misses = sum(1 for value in samples if value > stream.deadline_us)
            writer.writerow(
                [
                    stream.stream_id,
                    len(samples),
                    f"{(sum(samples) / len(samples)):.3f}" if samples else "0.000",
                    f"{max(samples):.3f}" if samples else "0.000",
                    misses,
                ]
            )

    reference = _read_reference(reference_path)
    validation_csv = output_path / "validation_report.csv"
    with validation_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "ID",
                "Analytical_WCRT_us",
                "Simulated_WCRT_us",
                "Analytical_over_Simulated",
                "Reference_WCRT_us",
                "Analytical_minus_Reference_us",
            ]
        )
        for stream in sorted(scenario.streams, key=lambda stream: stream.stream_id):
            if stream.priority not in AVB_CLASSES:
                continue
            ana = analytical.get(stream.stream_id)
            if ana is None:
                continue
            sim = simulation.max_response_time(stream.stream_id)
            ratio = (ana.total_wcrt_us / sim) if sim > 0 else 0.0
            ref = reference.get(stream.stream_id)
            writer.writerow(
                [
                    stream.stream_id,
                    f"{ana.total_wcrt_us:.3f}",
                    f"{sim:.3f}",
                    f"{ratio:.3f}",
                    f"{ref:.3f}" if ref is not None else "",
                    f"{(ana.total_wcrt_us - ref):.3f}" if ref is not None else "",
                ]
            )

    for link_id, points in simulation.credit_trace_by_link.items():
        trace_csv = output_path / f"credit_trace_{link_id}.csv"
        with trace_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time_us", "class_b_credit"])
            for time_us, credit in points:
                writer.writerow([f"{time_us:.6f}", f"{credit:.6f}"])


def write_cbs_sp_comparison_report(
    output_dir: str | Path,
    scenario: Scenario,
    analytical_cbs: Dict[int, AnalyticalResult],
    simulation_cbs: SimulationResult,
    analytical_sp: Dict[int, AnalyticalResult],
    simulation_sp: SimulationResult,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Main comparison — all stream classes including BE.
    # AVB rows carry analytical WCRTs; BE rows leave analytical columns blank because
    # BE has no CBS shaper and no analytical bound is defined.
    comparison_csv = output_path / "cbs_vs_sp_comparison.csv"
    with comparison_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "ID",
                "Class",
                "Deadline_us",
                "CBS_Analytical_us",
                "CBS_Simulated_WCRT_us",
                "CBS_Ratio_Analytical_over_Sim",
                "SP_Analytical_us",
                "SP_Simulated_WCRT_us",
                "SP_Ratio_Analytical_over_Sim",
                "CBS_Deadline_Miss_Sim",
                "SP_Deadline_Miss_Sim",
            ]
        )
        for stream in sorted(scenario.streams, key=lambda stream: stream.stream_id):
            cbs_sim = simulation_cbs.max_response_time(stream.stream_id)
            sp_sim = simulation_sp.max_response_time(stream.stream_id)

            if stream.priority in AVB_CLASSES:
                cbs_ana = analytical_cbs.get(stream.stream_id)
                sp_ana = analytical_sp.get(stream.stream_id)
                if cbs_ana is None or sp_ana is None:
                    continue
                cbs_ana_str = f"{cbs_ana.total_wcrt_us:.3f}"
                sp_ana_str = f"{sp_ana.total_wcrt_us:.3f}"
                cbs_ratio = (cbs_ana.total_wcrt_us / cbs_sim) if cbs_sim > 0 else 0.0
                sp_ratio = (sp_ana.total_wcrt_us / sp_sim) if sp_sim > 0 else 0.0
                cbs_ratio_str = f"{cbs_ratio:.3f}"
                sp_ratio_str = f"{sp_ratio:.3f}"
            else:
                # BE: no analytical bound
                cbs_ana_str = ""
                sp_ana_str = ""
                cbs_ratio_str = ""
                sp_ratio_str = ""

            writer.writerow(
                [
                    stream.stream_id,
                    stream.priority,
                    f"{stream.deadline_us:.3f}",
                    cbs_ana_str,
                    f"{cbs_sim:.3f}",
                    cbs_ratio_str,
                    sp_ana_str,
                    f"{sp_sim:.3f}",
                    sp_ratio_str,
                    int(cbs_sim > stream.deadline_us),
                    int(sp_sim > stream.deadline_us),
                ]
            )

    # BE starvation summary — the key deliverable for the optional SP extension.
    # A BE stream is "starved under SP" when it misses deadlines under SP but not under CBS,
    # which demonstrates the credit mechanism's role in protecting lower-priority queues.
    be_streams = [s for s in scenario.streams if s.priority not in AVB_CLASSES]
    if be_streams:
        starvation_csv = output_path / "be_starvation_summary.csv"
        with starvation_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "ID",
                    "Deadline_us",
                    "CBS_Simulated_WCRT_us",
                    "CBS_Samples",
                    "CBS_Deadline_Misses",
                    "CBS_Miss_Ratio",
                    "SP_Simulated_WCRT_us",
                    "SP_Samples",
                    "SP_Deadline_Misses",
                    "SP_Miss_Ratio",
                    "Starved_under_SP",
                ]
            )
            for stream in sorted(be_streams, key=lambda s: s.stream_id):
                cbs_samples = simulation_cbs.response_times_by_stream.get(stream.stream_id, [])
                sp_samples = simulation_sp.response_times_by_stream.get(stream.stream_id, [])
                cbs_misses = sum(1 for rt in cbs_samples if rt > stream.deadline_us)
                sp_misses = sum(1 for rt in sp_samples if rt > stream.deadline_us)
                cbs_miss_ratio = cbs_misses / len(cbs_samples) if cbs_samples else 0.0
                sp_miss_ratio = sp_misses / len(sp_samples) if sp_samples else 0.0
                starved = int(sp_miss_ratio > 0.0 and cbs_miss_ratio == 0.0)
                writer.writerow(
                    [
                        stream.stream_id,
                        f"{stream.deadline_us:.3f}",
                        f"{simulation_cbs.max_response_time(stream.stream_id):.3f}",
                        len(cbs_samples),
                        cbs_misses,
                        f"{cbs_miss_ratio:.4f}",
                        f"{simulation_sp.max_response_time(stream.stream_id):.3f}",
                        len(sp_samples),
                        sp_misses,
                        f"{sp_miss_ratio:.4f}",
                        starved,
                    ]
                )



