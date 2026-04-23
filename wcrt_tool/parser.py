from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .model import Scenario, Stream, Link


def _read_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_link_maps(topology_data: dict) -> tuple[Dict[str, Link], Dict[Tuple[str, str], str], set[str]]:
    topology = topology_data["topology"]
    switches = {switch["id"] for switch in topology.get("switches", [])}
    links: Dict[str, Link] = {}
    by_endpoints: Dict[Tuple[str, str], str] = {}

    for raw_link in topology.get("links", []):
        bandwidth_bps = float(raw_link.get("bandwidth_mbps", topology.get("default_bandwidth_mbps", 100))) * 1_000_000.0
        link = Link(
            link_id=raw_link["id"],
            source=raw_link["source"],
            destination=raw_link["destination"],
            bandwidth_bps=bandwidth_bps,
            delay_us=float(raw_link.get("delay", 0.0)),
        )
        links[link.link_id] = link
        by_endpoints[(link.source, link.destination)] = link.link_id

    return links, by_endpoints, switches


def _extract_path_nodes(route_entry: dict) -> Iterable[tuple[str, str]]:
    paths = route_entry.get("paths", [])
    if not paths:
        return []
    path_nodes = paths[0]
    pairs: List[tuple[str, str]] = []
    for index in range(len(path_nodes) - 1):
        pairs.append((path_nodes[index]["node"], path_nodes[index + 1]["node"]))
    return pairs


def load_scenario(
    topology_path: str | Path,
    streams_path: str | Path,
    routes_path: str | Path,
) -> Scenario:
    topology_data = _read_json(topology_path)
    streams_data = _read_json(streams_path)
    routes_data = _read_json(routes_path)

    links, link_by_endpoints, _switches = _build_link_maps(topology_data)
    routes_by_stream_id = {route["flow_id"]: route for route in routes_data.get("routes", [])}

    streams: List[Stream] = []
    warnings: List[str] = []

    for raw_stream in streams_data.get("streams", []):
        stream_id = int(raw_stream["id"])
        route = routes_by_stream_id.get(stream_id)
        if route is None:
            raise ValueError(f"Missing route for stream {stream_id}")

        path_links: List[str] = []
        for source_node, destination_node in _extract_path_nodes(route):
            link_id = link_by_endpoints.get((source_node, destination_node))
            if link_id is None:
                raise ValueError(
                    f"Cannot map route hop {source_node}->{destination_node} to topology link for stream {stream_id}"
                )
            path_links.append(link_id)

        if not path_links:
            raise ValueError(f"Stream {stream_id} has an empty path in routes.json")

        destination = raw_stream.get("destinations", [{}])[0]
        streams.append(
            Stream(
                stream_id=stream_id,
                name=str(raw_stream.get("name", f"stream_{stream_id}")),
                source=str(raw_stream["source"]),
                destination=str(destination.get("id", "")),
                priority=int(raw_stream.get("PCP", 0)),
                size_bytes=int(raw_stream["size"]),
                period_us=int(raw_stream["period"]),
                deadline_us=float(destination.get("deadline", raw_stream["period"])),
                path_links=tuple(path_links),
            )
        )
        if streams[-1].deadline_us > float(streams[-1].period_us):
            warnings.append(
                f"Stream {stream_id}: D_i ({streams[-1].deadline_us}) > T_i ({streams[-1].period_us}); analysis assumes D_i <= T_i."
            )

    return Scenario(links=links, streams=streams, warnings=warnings)



