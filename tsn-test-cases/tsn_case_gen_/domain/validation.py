#!/usr/bin/env python3
"""
validation.py

Domain utility for universal validation of TSN JSON files against all known schemas (config, topology, streams, routes).

This module provides a CLI tool and functions to validate any TSN JSON file by attempting to match it against all supported schemas.
It is used to quickly check the structure of generated or user-supplied files for compliance with project specifications.

Features:
    - Defines all major TSN JSON schemas (config, topology, streams, routes).
    - Validates a file against each schema, reporting the first successful match.
    - CLI interface for batch or manual validation.
    - Suppresses error output for non-matching schemas, only reports success or failure.

Usage:
    python universal_validate.py --json FILE

Main Functions:
    - validate_with_schema: Validates data against a given schema.
    - main: CLI entry point for universal validation.

Raises:
    - Prints error messages and exits with code 1 for invalid files or no matching schema.
"""

import sys
import json
from typing import Dict, Any
from test_case_validation import (
    GEN_CONFIG_SCHEMA,
    TOPOLOGY_SCHEMA,
    STREAMS_SCHEMA,
    ROUTES_SCHEMA
)
from jsonschema import validate as js_validate

# Try to import the Pydantic config model
try:
    from jsonschema import validate as js_validate
except ImportError:
    ConfigV2 = None

SCHEMAS = [
    ("topology.json", TOPOLOGY_SCHEMA),
    ("streams.json", STREAMS_SCHEMA),
    ("routes.json", ROUTES_SCHEMA),
    ("gen_config.json", GEN_CONFIG_SCHEMA),
]


def validate_with_schema(data: Dict[str, Any], schema: Dict[str, Any], name: str) -> bool:
    try:
        js_validate(data, schema)
        return True
    except Exception:
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Universal TSN JSON validator")
    parser.add_argument("--json", required=True, help="Path to JSON file to validate.")
    args = parser.parse_args()

    try:
        with open(args.json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read JSON: {e}")
        sys.exit(1)



    # Try each jsonschema, only print the successful one
    for name, schema in SCHEMAS:
        if validate_with_schema(data, schema, name):
            print(f"✅ Valid {name} structure (jsonschema)")
            sys.exit(0)
    print("❌ No matching schema found or validation failed.")
    sys.exit(1)

if __name__ == "__main__":
    main()
