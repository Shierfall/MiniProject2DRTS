from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .model import AVB_CLASSES, CLASS_A, CLASS_B, Scenario, Stream


@dataclass
class LinkBreakdown:
    link_id: str
    c_i_us: float
    spi_us: float
    hpi_us: float
    lpi_us: float
    total_us: float


@dataclass
class AnalyticalResult:
    stream: Stream
    total_wcrt_us: float
    per_link: List[LinkBreakdown]


def build_alpha_plus_map(
    scenario: Scenario,
    policy: str = "fixed",
    alpha_a: float = 0.5,
    alpha_b: float = 0.5,
) -> Dict[str, Dict[int, float]]:
    alpha_by_link: Dict[str, Dict[int, float]] = {}
    eps = 1e-6

    for link_id in scenario.links:
        if policy == "fixed":
            a_plus = max(eps, min(alpha_a, 1.0 - eps))
            b_plus = max(eps, min(alpha_b, 1.0 - eps))
        elif policy == "proportional":
            u_by_class = {2: 0.0, 1: 0.0, 0: 0.0}
            for stream in scenario.streams_on_link(link_id):
                link = scenario.links[link_id]
                u_by_class[stream.priority] += stream.tx_time_us(link) / float(stream.period_us)

            u_avb = u_by_class[2] + u_by_class[1]
            u_be = u_by_class[0]
            available = max(0.0, 1.0 - u_be)
            if u_avb <= 0.0:
                a_plus = max(eps, min(alpha_a, 1.0 - eps))
                b_plus = max(eps, min(alpha_b, 1.0 - eps))
            else:
                a_plus = max(eps, min((u_by_class[2] / u_avb) * available, 1.0 - eps))
                b_plus = max(eps, min((u_by_class[1] / u_avb) * available, 1.0 - eps))
        else:
            raise ValueError(f"Unknown slope policy: {policy}")

        alpha_by_link[link_id] = {CLASS_A: a_plus, CLASS_B: b_plus}

        if a_plus + b_plus > 1.0:
            scenario.warnings.append(
                f"Link {link_id}: alpha_plus_A + alpha_plus_B > 1.0 ({a_plus + b_plus:.6f})"
            )

        # Spec validity check: sum of reserved bandwidth of priorities >= P_j must be <= 1.
        rbw_ge_a = a_plus
        rbw_ge_b = a_plus + b_plus
        if rbw_ge_a > 1.0 + 1e-9:
            scenario.warnings.append(f"Link {link_id}: RBW(P>=A)={rbw_ge_a:.6f} exceeds 1.0")
        if rbw_ge_b > 1.0 + 1e-9:
            scenario.warnings.append(f"Link {link_id}: RBW(P>=B)={rbw_ge_b:.6f} exceeds 1.0")

    return alpha_by_link


def _alpha_minus(alpha_plus: float) -> float:
    return 1.0 - alpha_plus


def _max_tx_time(streams: List[Stream], link_id: str, scenario: Scenario) -> float:
    if not streams:
        return 0.0
    link = scenario.links[link_id]
    return max(stream.tx_time_us(link) for stream in streams)


def compute_cbs_wcrt(
    scenario: Scenario,
    alpha_plus_by_link: Dict[str, Dict[int, float]],
) -> Dict[int, AnalyticalResult]:
    results: Dict[int, AnalyticalResult] = {}

    for stream in scenario.streams:
        if stream.priority not in AVB_CLASSES:
            continue

        total_wcrt = 0.0
        breakdowns: List[LinkBreakdown] = []

        for link_id in stream.path_links:
            link = scenario.links[link_id]
            c_i = stream.tx_time_us(link)
            alpha_plus = alpha_plus_by_link[link_id][stream.priority]
            alpha_minus = _alpha_minus(alpha_plus)

            same_priority = [
                other
                for other in scenario.streams_on_link(link_id)
                if other.stream_id != stream.stream_id and other.priority == stream.priority
            ]
            spi = sum(other.tx_time_us(link) * (1.0 + alpha_minus / alpha_plus) for other in same_priority)

            lower_priority = [
                other for other in scenario.streams_on_link(link_id) if other.priority < stream.priority
            ]
            lpi = _max_tx_time(lower_priority, link_id, scenario)

            if stream.priority == CLASS_A:
                hpi = 0.0
            else:
                higher_priority = [
                    other for other in scenario.streams_on_link(link_id) if other.priority > stream.priority
                ]
                if higher_priority:
                    alpha_h_plus = alpha_plus_by_link[link_id][CLASS_A]
                    alpha_h_minus = _alpha_minus(alpha_h_plus)
                    max_c_h = _max_tx_time(higher_priority, link_id, scenario)
                    hpi = lpi * (alpha_h_plus / alpha_h_minus) + max_c_h
                else:
                    hpi = 0.0

            wcrt_link = spi + hpi + lpi + c_i
            total_wcrt += wcrt_link
            breakdowns.append(
                LinkBreakdown(
                    link_id=link_id,
                    c_i_us=c_i,
                    spi_us=spi,
                    hpi_us=hpi,
                    lpi_us=lpi,
                    total_us=wcrt_link,
                )
            )

        results[stream.stream_id] = AnalyticalResult(stream=stream, total_wcrt_us=total_wcrt, per_link=breakdowns)

    return results


def compute_sp_wcrt(scenario: Scenario) -> Dict[int, AnalyticalResult]:
    results: Dict[int, AnalyticalResult] = {}

    for stream in scenario.streams:
        if stream.priority not in AVB_CLASSES:
            continue

        total_wcrt = 0.0
        per_link: List[LinkBreakdown] = []

        for link_id in stream.path_links:
            link = scenario.links[link_id]
            c_i = stream.tx_time_us(link)
            lower = [other for other in scenario.streams_on_link(link_id) if other.priority < stream.priority]
            higher = [other for other in scenario.streams_on_link(link_id) if other.priority > stream.priority]
            blocking = max((other.tx_time_us(link) for other in lower), default=0.0)

            r_prev = c_i
            while True:
                interference = 0.0
                for higher_stream in higher:
                    c_h = higher_stream.tx_time_us(link)
                    jobs = int(-(-r_prev // higher_stream.period_us))
                    interference += jobs * c_h
                r_next = c_i + blocking + interference
                if abs(r_next - r_prev) <= 1e-9 or r_next > stream.deadline_us:
                    break
                r_prev = r_next

            total_wcrt += r_next
            per_link.append(
                LinkBreakdown(
                    link_id=link_id,
                    c_i_us=c_i,
                    spi_us=0.0,
                    hpi_us=interference,
                    lpi_us=blocking,
                    total_us=r_next,
                )
            )

        results[stream.stream_id] = AnalyticalResult(stream=stream, total_wcrt_us=total_wcrt, per_link=per_link)

    return results


