from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from itertools import count
from typing import Dict, List, Tuple

from .model import AVB_CLASSES, CLASS_A, CLASS_B, CLASS_BE, Frame, PortState, Scenario, lcm

ARRIVAL_EVENT = "arrival"
TX_START_EVENT = "tx_start"
TX_END_EVENT = "tx_end"

EVENT_PRIORITY = {
    ARRIVAL_EVENT: 0,
    TX_END_EVENT: 1,
    TX_START_EVENT: 2,
}

CREDIT_EPS = 1e-9
TIME_EPS_US = 1e-6


@dataclass
class SimulationResult:
    response_times_by_stream: Dict[int, List[float]] = field(default_factory=dict)
    credit_trace_by_link: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)

    def max_response_time(self, stream_id: int) -> float:
        values = self.response_times_by_stream.get(stream_id, [])
        return max(values) if values else 0.0

    def avg_response_time(self, stream_id: int) -> float:
        values = self.response_times_by_stream.get(stream_id, [])
        return sum(values) / len(values) if values else 0.0


@dataclass
class _Event:
    time_us: float
    kind: str
    link_id: str
    frame: Frame | None = None


class _EventQueue:
    def __init__(self) -> None:
        self._items: List[tuple[float, int, int, _Event]] = []
        self._seq = count()

    def push(self, event: _Event) -> None:
        heapq.heappush(
            self._items,
            (event.time_us, EVENT_PRIORITY[event.kind], next(self._seq), event),
        )

    def pop(self) -> _Event:
        return heapq.heappop(self._items)[3]

    def __bool__(self) -> bool:
        return bool(self._items)


def _alpha_minus(alpha_plus: float) -> float:
    return 1.0 - alpha_plus


def _accrue_credit(port: PortState, link_bandwidth_bps: float, now_us: float, mode: str) -> None:
    dt = now_us - port.last_update_us
    if dt <= 0.0:
        return

    if mode == "sp":
        port.last_update_us = now_us
        return

    if port.busy and port.current_priority is not None:
        tx_class = port.current_priority
        for traffic_class in AVB_CLASSES:
            if traffic_class == tx_class:
                port.credit[traffic_class] -= dt * _alpha_minus(port.alpha_plus[traffic_class])
            elif port.queues[traffic_class]:
                # Waiting class accumulates credit while blocked by a higher-class transmission
                port.credit[traffic_class] += dt * port.alpha_plus[traffic_class]
    else:
        # Port idle: credit only accumulates when negative and frames are queued (blocked state).
        # If queue is empty and credit is positive, reset to 0 (CBS idle rule).
        for traffic_class in AVB_CLASSES:
            if port.queues[traffic_class]:
                if port.credit[traffic_class] < 0.0:
                    port.credit[traffic_class] += dt * port.alpha_plus[traffic_class]
            elif port.credit[traffic_class] > 0.0:
                port.credit[traffic_class] = 0.0

    max_tx_time_us = (1542.0 * 8.0 / link_bandwidth_bps) * 1_000_000.0
    for traffic_class in AVB_CLASSES:
        lower_cap = -max_tx_time_us * _alpha_minus(port.alpha_plus[traffic_class])
        port.credit[traffic_class] = max(port.credit[traffic_class], lower_cap)

    port.last_update_us = now_us


def simulate(
    scenario: Scenario,
    alpha_plus_by_link: Dict[str, Dict[int, float]],
    duration_us: float | None = None,
    mode: str = "cbs",
    capture_credit_trace: bool = False,
) -> SimulationResult:
    hyperperiod_us = float(lcm(scenario.periods))
    min_horizon_us = 2.0 * hyperperiod_us
    requested_horizon = float(duration_us) if duration_us is not None else min_horizon_us
    horizon = max(requested_horizon, min_horizon_us)
    warmup_cutoff_us = hyperperiod_us

    result = SimulationResult(
        response_times_by_stream={stream.stream_id: [] for stream in scenario.streams},
        credit_trace_by_link={link_id: [] for link_id in scenario.links} if capture_credit_trace and mode == "cbs" else {},
    )
    ports: Dict[str, PortState] = {
        link_id: PortState(link_id=link_id, alpha_plus=alpha_plus_by_link[link_id].copy()) for link_id in scenario.links
    }
    event_queue = _EventQueue()
    pending_tx_start_us: Dict[str, float | None] = {link_id: None for link_id in scenario.links}

    def schedule_tx_start(link_id: str, when_us: float) -> None:
        existing = pending_tx_start_us[link_id]
        target = when_us if when_us > 0.0 else 0.0
        if existing is not None and existing <= target + TIME_EPS_US:
            return
        pending_tx_start_us[link_id] = target
        event_queue.push(_Event(time_us=target, kind=TX_START_EVENT, link_id=link_id))

    for stream in scenario.streams:
        if not stream.path_links:
            continue
        release = 0.0
        job = 0
        while release <= horizon:
            frame = Frame(
                stream_id=stream.stream_id,
                priority=stream.priority,
                size_bytes=stream.size_bytes,
                deadline_us=stream.deadline_us,
                release_time_us=release,
                remaining_links=list(stream.path_links),
            )
            first_link = frame.remaining_links.pop(0)
            event_queue.push(_Event(time_us=release, kind=ARRIVAL_EVENT, link_id=first_link, frame=frame))
            job += 1
            release = job * stream.period_us

    while event_queue:
        event = event_queue.pop()
        if event.time_us > horizon:
            break

        if event.kind == TX_START_EVENT:
            expected = pending_tx_start_us[event.link_id]
            if expected is None or abs(expected - event.time_us) > TIME_EPS_US:
                continue
            pending_tx_start_us[event.link_id] = None

        port = ports[event.link_id]
        link = scenario.links[event.link_id]
        _accrue_credit(port, link.bandwidth_bps, event.time_us, mode)
        if capture_credit_trace and mode == "cbs":
            trace = result.credit_trace_by_link[event.link_id]
            current_credit_b = port.credit[CLASS_B]
            if not trace or abs(trace[-1][0] - event.time_us) > TIME_EPS_US or abs(trace[-1][1] - current_credit_b) > CREDIT_EPS:
                trace.append((event.time_us, current_credit_b))

        if event.kind == ARRIVAL_EVENT:
            assert event.frame is not None
            port.queues[event.frame.priority].append(event.frame)
            if not port.busy:
                schedule_tx_start(event.link_id, event.time_us)

        elif event.kind == TX_START_EVENT:
            if port.busy:
                continue

            chosen_class = None
            for traffic_class in (CLASS_A, CLASS_B, CLASS_BE):
                if not port.queues[traffic_class]:
                    continue
                if mode == "cbs" and traffic_class in AVB_CLASSES and port.credit[traffic_class] < -CREDIT_EPS:
                    continue
                chosen_class = traffic_class
                break

            if chosen_class is None:
                if mode == "cbs":
                    ready_at = []
                    for traffic_class in AVB_CLASSES:
                        if port.queues[traffic_class] and port.credit[traffic_class] < -CREDIT_EPS:
                            alpha = max(port.alpha_plus[traffic_class], 1e-9)
                            wait_us = abs(port.credit[traffic_class]) / alpha
                            ready_at.append(max(event.time_us + TIME_EPS_US, event.time_us + wait_us))
                    if ready_at:
                        schedule_tx_start(event.link_id, min(ready_at))
                continue

            frame = port.queues[chosen_class].pop(0)
            port.busy = True
            port.current_frame = frame
            port.current_priority = chosen_class
            tx_time_us = (frame.size_bytes * 8.0 / link.bandwidth_bps) * 1_000_000.0
            event_queue.push(
                _Event(
                    time_us=event.time_us + tx_time_us,
                    kind=TX_END_EVENT,
                    link_id=event.link_id,
                    frame=frame,
                )
            )

        elif event.kind == TX_END_EVENT:
            frame = event.frame if event.frame is not None else port.current_frame
            port.busy = False
            port.current_frame = None
            port.current_priority = None

            if mode == "cbs":
                for traffic_class in AVB_CLASSES:
                    if not port.queues[traffic_class] and port.credit[traffic_class] > 0.0:
                        port.credit[traffic_class] = 0.0

            if frame is None:
                continue

            if frame.remaining_links:
                next_link = frame.remaining_links.pop(0)
                event_queue.push(_Event(time_us=event.time_us, kind=ARRIVAL_EVENT, link_id=next_link, frame=frame))
            else:
                rt = event.time_us - frame.release_time_us
                if frame.release_time_us >= warmup_cutoff_us:
                    result.response_times_by_stream[frame.stream_id].append(rt)

            if any(port.queues[traffic_class] for traffic_class in (CLASS_A, CLASS_B, CLASS_BE)):
                schedule_tx_start(event.link_id, event.time_us)

    return result




