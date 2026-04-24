#!/usr/bin/env python3
"""
config_validation.py

Domain module for validating TSN simulation configuration files.

This module provides two-stage validation for TSN config JSON files:
    1. Structural validation using Pydantic models for type safety and fast checks.
    2. Per-traffic-type validation using small, type-specific JSON Schemas (Draft 2020-12).

Features:
    - Defines Pydantic models for all major config sections (General, Network, Routing, DomainConnections, Traffic).
    - Provides small JSON Schemas for each supported traffic type, enforcing strict field requirements.
    - Validates each traffic type in the config against its schema, reporting detailed errors.
    - CLI entry point for standalone validation: `python config_validation.py <config.json>`.

Usage:
    python config_validation.py <config.json>

Dependencies:
    - pydantic>=2
    - jsonschema>=4

Main Classes:
    - ConfigV2: Top-level config model with validation method.
    - TrafficType, CycleTime, etc.: Sub-models for config sections.

Main Functions:
    - validate_per_traffic_type: Validates each traffic type against its schema.
    - main: CLI entry point for config validation.

Raises:
    - pydantic.ValidationError: For structural errors in config.
    - ValueError: For per-traffic-type schema mismatches.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
import json
import sys
# ---------- Per-traffic-type JSON-Schema validation ----------

from jsonschema import Draft202012Validator, exceptions as js_exceptions

# ---------- Pydantic models (overall structure) ----------

class TopologySize(BaseModel):
    num_switches: int = Field(..., ge=1)
    num_end_systems: int = Field(..., ge=1)
    # Pydantic v2: use min_length/max_length for list constraints
    end_systems_per_switch: List[int] = Field(..., min_length=2, max_length=2)

class General(BaseModel):
    output_directory: str
    num_test_cases: int = Field(..., ge=1)
    num_domains: int = Field(..., ge=1)
    topology_size: TopologySize
    cross_domain_streams: int = Field(..., ge=0)
    generate_routes: Optional[bool] = None
    test_case_naming: str

class NetworkConstraints(BaseModel):
    max_path_length: int = Field(..., ge=1)
    min_redundant_paths: Optional[int] = Field(None, ge=0)

class Network(BaseModel):
    topology_type: str
    parameters: str
    default_bandwidth_mbps: int = Field(..., ge=1)
    constraints: NetworkConstraints

class Routing(BaseModel):
    algorithm: Optional[str] = None
    consider_link_utilization: bool

class DomainConnections(BaseModel):
    type: str
    connections_per_domain_pair: int = Field(..., ge=1)

class CycleTime(BaseModel):
    cycle_time_units: str
    choose_list: bool
    cycle_time_list: List[int] = Field(..., min_length=1)
    min_cycle_time: int = Field(..., ge=1)
    max_cycle_time: int = Field(..., ge=1)

class TrafficType(BaseModel):
    name: str
    PCP_list: List[int] = Field(..., min_length=1, alias="PCP-list")
    number: int = Field(..., ge=0)
    redundant_number: Optional[int] = Field(None, ge=0)
    redundant_routes: Optional[int] = Field(None, ge=0)
    # IMPORTANT: make truly optional by giving a default of None
    cycle_time: Optional[CycleTime] = None
    min_delay: Optional[int] = Field(None, ge=0)
    max_delay: Optional[int] = Field(None, ge=0)
    min_packet_size: int = Field(..., ge=1)
    max_packet_size: int = Field(..., ge=1)
    bidirectional: bool

class Traffic(BaseModel):
    types: List[TrafficType] = Field(..., min_length=1)

class ConfigV2(BaseModel):
    delay_units: str
    general: General
    network: Network
    routing: Routing
    domain_connections: DomainConnections
    traffic: Traffic

    @classmethod
    def validate_json(cls, data: Dict[str, Any]):
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            print("Validation error (Pydantic structure):")
            print(e)
            raise


# ---------- Small per-traffic-type JSON Schemas (Draft 2020-12) ----------

def _cycle_and_redundancy_schema(name: str) -> Dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name,
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"const": name},
            "PCP-list": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "integer", "minimum": 0, "maximum": 7}
            },
            "number": {"type": "integer", "minimum": 0},
            "redundant_number": {"type": "integer", "minimum": 0},
            "redundant_routes": {"type": "integer", "minimum": 0},
            "cycle_time": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "cycle_time_units": {
                        "type": "string",
                        "enum": ["NANO_SECOND", "MICRO_SECOND", "MILLI_SECOND", "SECOND"]
                    },
                    "choose_list": {"type": "boolean"},
                    "cycle_time_list": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "integer", "minimum": 1}
                    },
                    "min_cycle_time": {"type": "integer", "minimum": 1},
                    "max_cycle_time": {"type": "integer", "minimum": 1}
                },
                "required": [
                    "cycle_time_units",
                    "choose_list",
                    "cycle_time_list",
                    "min_cycle_time",
                    "max_cycle_time"
                ]
            },
            "min_delay": {"type": "integer", "minimum": 0},
            "max_delay": {"type": "integer", "minimum": 0},
            "min_packet_size": {"type": "integer", "minimum": 1},
            "max_packet_size": {"type": "integer", "minimum": 1},
            "bidirectional": {"type": "boolean"}
        },
        "required": [
            "name",
            "PCP-list",
            "number",
            "redundant_number",
            "redundant_routes",
            "cycle_time",
            "min_delay",
            "max_delay",
            "min_packet_size",
            "max_packet_size",
            "bidirectional"
        ]
    }

def _audio_voice_schema() -> Dict[str, Any]:
    name = "AUDIO/VOICE"
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name,
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"const": name},
            "PCP-list": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "integer", "minimum": 0, "maximum": 7}
            },
            "number": {"type": "integer", "minimum": 0},
            "min_delay": {"type": "integer", "minimum": 0},
            "max_delay": {"type": "integer", "minimum": 0},
            "min_packet_size": {"type": "integer", "minimum": 1},
            "max_packet_size": {"type": "integer", "minimum": 1},
            "bidirectional": {"type": "boolean"}
        },
        "required": [
            "name",
            "PCP-list",
            "number",
            "min_delay",
            "max_delay",
            "min_packet_size",
            "max_packet_size",
            "bidirectional"
        ]
    }

def _best_effort_schema() -> Dict[str, Any]:
    name = "BEST-EFFORT"
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name,
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"const": name},
            "PCP-list": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "integer", "minimum": 0, "maximum": 7}
            },
            "number": {"type": "integer", "minimum": 0},
            "min_packet_size": {"type": "integer", "minimum": 1},
            "max_packet_size": {"type": "integer", "minimum": 1},
            "bidirectional": {"type": "boolean"}
        },
        "required": [
            "name",
            "PCP-list",
            "number",
            "min_packet_size",
            "max_packet_size",
            "bidirectional"
        ]
    }

TRAFFIC_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "ISOCHRONOUS": _cycle_and_redundancy_schema("ISOCHRONOUS"),
    "CYCLIC-SYNCHRONOUS": _cycle_and_redundancy_schema("CYCLIC-SYNCHRONOUS"),
    "CYCLIC-ASYNCHRONOUS": _cycle_and_redundancy_schema("CYCLIC-ASYNCHRONOUS"),
    "NETWORK-CONTROL": _cycle_and_redundancy_schema("NETWORK-CONTROL"),
    "ALARMS-AND-EVENTS": _cycle_and_redundancy_schema("ALARMS-AND-EVENTS"),
    "DIAGNOSTICS": _cycle_and_redundancy_schema("DIAGNOSTICS"),
    "VIDEO": _cycle_and_redundancy_schema("VIDEO"),
    "BEST-EFFORT": _best_effort_schema(),
    "AUDIO/VOICE": _audio_voice_schema(),
}




def validate_per_traffic_type(data: Dict[str, Any]) -> None:
    """
    Validate each traffic.types[i] against its small schema chosen by `name`.
    Raises ValueError with a summary if any mismatch occurs.
    """
    items = (data.get("traffic") or {}).get("types") or []
    errors: List[str] = []

    for idx, item in enumerate(items):
        tname = item.get("name")
        schema = TRAFFIC_SCHEMAS.get(tname)
        if not schema:
            errors.append(f"[types[{idx}]] name='{tname}': no schema found for this traffic type")
            continue
        try:
            Draft202012Validator(schema).validate(item)
        except js_exceptions.ValidationError as e:
            loc = " → ".join(str(p) for p in e.absolute_path) or "(root)"
            errors.append(f"[types[{idx}]] name='{tname}': {e.message} at {loc}")

    if errors:
        msg = "Traffic type validation failed:\n" + "\n".join(errors)
        raise ValueError(msg)


# ---------- CLI ----------

def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("Usage: python validation.py <config.json>")
        return 1

    config_path = argv[1]
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read JSON: {e}")
        return 1

    # 1) Pydantic structural validation
    try:
        ConfigV2.validate_json(data)
    except ValidationError:
        return 1

    # 2) Per-traffic-type JSON Schema validation
    try:
        validate_per_traffic_type(data)
    except ValueError as e:
        print(str(e))
        return 1

    print("✅ Config is valid (Pydantic structure + per-traffic-type schemas).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
