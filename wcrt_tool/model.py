from __future__ import annotations

from dataclasses import dataclass, field
from math import gcd
from typing import Dict, List, Tuple


CLASS_A = 2
CLASS_B = 1
CLASS_BE = 0
AVB_CLASSES = (CLASS_A, CLASS_B)


def lcm(values: List[int]) -> int:
    result = 1
    for value in values:
        if value <= 0:
            continue
        result = result * value // gcd(result, value)
    return max(result, 1)


@dataclass(frozen=True)
class Link:
    link_id: str
    source: str
    destination: str
    bandwidth_bps: float
    delay_us: float


@dataclass(frozen=True)
class Stream:
    stream_id: int
    name: str
    source: str
    destination: str
    priority: int
    size_bytes: int
    period_us: int
    deadline_us: float
    path_links: Tuple[str, ...]

    def tx_time_us(self, link: Link) -> float:
        return (self.size_bytes * 8.0 / link.bandwidth_bps) * 1_000_000.0


@dataclass
class Scenario:
    links: Dict[str, Link]
    streams: List[Stream]
    warnings: List[str] = field(default_factory=list)

    def streams_on_link(self, link_id: str) -> List[Stream]:
        return [stream for stream in self.streams if link_id in stream.path_links]

    @property
    def periods(self) -> List[int]:
        return [stream.period_us for stream in self.streams]


@dataclass
class Frame:
    stream_id: int
    priority: int
    size_bytes: int
    deadline_us: float
    release_time_us: float
    remaining_links: List[str]


@dataclass
class PortState:
    link_id: str
    alpha_plus: Dict[int, float]
    queues: Dict[int, List[Frame]] = field(default_factory=lambda: {CLASS_A: [], CLASS_B: [], CLASS_BE: []})
    credit: Dict[int, float] = field(default_factory=lambda: {CLASS_A: 0.0, CLASS_B: 0.0})
    busy: bool = False
    current_frame: Frame | None = None
    current_priority: int | None = None
    last_update_us: float = 0.0

