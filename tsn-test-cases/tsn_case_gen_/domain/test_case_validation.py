"""
test_case_validation.py

Domain module for validating generated TSN test case JSON files against project specifications.

This module provides functions to validate topology, streams, routes, and config files using JSON schemas and integrity checks.
It enforces the rules described in file_format_specs.v2.md and ensures all generated files are consistent and correct.

Features:
    - Defines JSON schemas for topology, streams, routes, and config files.
    - Validates files against schemas and checks for required fields, types, and value ranges.
    - Performs integrity checks (e.g., node/link existence, port usage, stream deadlines, route correctness).
    - Aggregates errors for comprehensive validation reporting.

Usage:
    errors = validate_all(topology, streams, routes)
    if errors:
        print("Validation errors:", errors)

Main Functions:
    - validate_gen_config: Validates gen_config.json against schema.
    - validate_topology: Validates topology.json against schema and integrity rules.
    - validate_streams: Validates streams.json against schema and integrity rules.
    - validate_routes: Validates routes.json against schema and integrity rules.
    - validate_all: Validates all files together and aggregates errors.

Raises:
    - Returns error lists for reporting; does not raise exceptions directly.
"""

import logging
from typing import Dict, List, Optional
import jsonschema

logger = logging.getLogger(__name__)

# JSON schema for topology.json
TOPOLOGY_SCHEMA = {
    "type": "object",
    "properties": {
        "topology": {
            "type": "object",
            "required": ["switches", "end_systems", "links"],
            "properties": {
                "default_bandwidth_mbps": { "type": "number" },
                "delay_units": { "type": "string" },
                "switches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "ports", "domain"],
                        "properties": {
                            "id": { "type": "string" },
                            "ports": { "type": "integer" },
                            "domain": { "type": "integer" }
                        },
                        "additionalProperties": True
                    }
                },
                "end_systems": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "domain"],
                        "properties": {
                            "id": { "type": "string" },
                            "domain": { "type": "integer" }
                        },
                        "additionalProperties": True
                    }
                },
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "source", "destination", "sourcePort", "destinationPort", "domain"],
                        "properties": {
                            "id": { "type": "string" },
                            "source": { "type": "string" },
                            "destination": { "type": "string" },
                            "sourcePort": { "type": "integer" },
                            "destinationPort": { "type": "integer" },
                            "bandwidth_mbps": { "type": "number" },
                            "delay": { "type": "number" },
                            "domain": { "type": "integer" }
                        },
                        "additionalProperties": True
                    }
                }
            },
            "additionalProperties": True
        }
    },
    "required": ["topology"],
    "additionalProperties": True
}

# JSON schema for streams.json
STREAMS_SCHEMA = {
    "type": "object",
    "required": ["delay_units", "streams"],
    "properties": {
        "delay_units": {"type": "string"},
        "streams": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "source", "destinations", "type", "PCP", "size", "period"],
                "properties": {
                    "id": { "type": "integer" },
                    "name": { "type": "string" },
                    "source": { "type": "string" },
                    "destinations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id", "deadline"],
                            "properties": {
                                "id": { "type": "string" },
                                "deadline": { "type": ["number", "null"] }
                            }
                        }
                    },
                    "type": { "type": "string" },
                    "PCP": { "type": "integer" },
                    "size": { "type": "integer" },
                    "period": { "type": ["integer", "null"] },
                    "redundancy": { "type": "integer" }
                },
                "additionalProperties": True
            }
        }
    },
    "additionalProperties": True
}

# JSON schema for routes.json
ROUTES_SCHEMA = {
    "type": "object",
    "required": ["delay_units", "routes"],
    "properties": {
        "delay_units": {"type": "string"},
        "routes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["flow_id", "paths"],
                "properties": {
                    "flow_id": {"type": "integer"},
                    "paths": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["node", "port"],
                                "properties": {
                                    "node": {"type": "string"},
                                    "port": {"type": "integer", "minimum": 0}
                                },
                                "additionalProperties": True
                            }
                        }
                    },
                    "min_e2e_delay": {"type": "number", "minimum": 0}
                },
                "additionalProperties": True
            }
        }
    },
    "additionalProperties": True
}

# JSON schema for gen_config.json
GEN_CONFIG_SCHEMA = {
  "type": "object",
  "required": ["general", "network", "traffic"],
  "properties": {
    "delay_units": { "type": "string" },
    "general": {
      "type": "object",
      "required": ["output_directory", "num_test_cases", "topology_size"],
      "properties": {
        "output_directory": { "type": "string" },
        "num_test_cases": { "type": "integer", "minimum": 1 },
        "num_domains": { "type": "integer", "minimum": 1 },
        "test_case_naming": { "type": "string" },
        "topology_size": {
          "type": "object",
          "required": ["num_switches", "num_end_systems"],
          "properties": {
            "num_switches": { "type": "integer", "minimum": 1 },
            "num_end_systems": { "type": "integer", "minimum": 1 },
            "end_systems_per_switch": {
              "type": "array",
              "items": { "type": "integer" }
            }
          },
          "additionalProperties": True
        },
        "cross_domain_streams": { "type": "integer", "minimum": 0 },
        "generate_routes": { "type": "boolean" }
      },
      "additionalProperties": True
    },
    "network": {
      "type": "object",
      "required": ["topology_type", "parameters"],
      "properties": {
        "topology_type": { "type": "string" },
        "parameters": { "type": "string" },
        "default_bandwidth_mbps": { "type": "integer", "minimum": 1 },
        "constraints": {
          "type": "object",
          "properties": {
            "max_path_length": { "type": "integer", "minimum": 1 },
            "min_redundant_paths": { "type": "integer", "minimum": 1 }
          },
          "additionalProperties": True
        }
      },
      "additionalProperties": True
    },
    "routing": {
      "type": "object",
      "properties": {
        "algorithm": { 
          "type": "string",
          "enum": ["shortest_path"]
        },
        "consider_link_utilization": { "type": "boolean" }
      },
      "additionalProperties": True
    },
    "domain_connections": {
      "type": "object",
      "properties": {
        "type": { "type": "string" },
        "connections_per_domain_pair": { "type": "integer", "minimum": 1 }
      },
      "additionalProperties": True
    },
    "traffic": {
      "type": "object",
      "required": ["types"],
      "properties": {
        "types": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "number"],
            "properties": {
              "name": { "type": "string" },
              "PCP-list": {
                "type": "array",
                "items": { "type": "integer", "minimum": 0, "maximum": 7 }
              },
              "number": { "type": "integer", "minimum": 0 },
              "redundant_number": { "type": "integer", "minimum": 0 },
              "redundant_routes": { "type": "integer", "minimum": 0 },
              "cycle_time": {
                "type": "object",
                "properties": {
                  "cycle_time_units": { "type": "string" },
                  "choose_list": { "type": "boolean" },
                  "cycle_time_list": {
                    "type": "array",
                    "items": { "type": "integer", "minimum": 1 }
                  },
                  "min_cycle_time": { "type": "integer", "minimum": 1 },
                  "max_cycle_time": { "type": "integer", "minimum": 1 }
                },
                "additionalProperties": True
              },
              "period_us": {
                "oneOf": [
                  { "type": "integer", "minimum": 1 },
                  {
                    "type": "array",
                    "items": { "type": "integer", "minimum": 1 }
                  }
                ]
              },
              "min_delay": { "type": "integer", "minimum": 1 },
              "max_delay": { "type": "integer", "minimum": 1 },
              "deadline_min_us": { "type": "integer", "minimum": 1 },
              "deadline_max_us": { "type": "integer", "minimum": 1 },
              "size_bytes_min": { "type": "integer", "minimum": 1 },
              "size_bytes_max": { "type": "integer", "minimum": 1 },
              "min_packet_size": { "type": "integer", "minimum": 1 },
              "max_packet_size": { "type": "integer", "minimum": 1 },
              "bidirectional": { "type": "boolean" }
            },
            "additionalProperties": True
          }
        }
      },
      "additionalProperties": True
    }
  },
  "additionalProperties": True
}


def validate_gen_config(config: Dict) -> List[str]:
    """
    Validate the gen_config.json file.
    
    Args:
        config: The configuration to validate
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    return _validate_against_schema(config, GEN_CONFIG_SCHEMA, "gen_config.json")

def validate_topology(topology: Dict) -> List[str]:
    """
    Validate the topology.json file.
    
    Args:
        topology: The topology to validate
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    errors = _validate_against_schema(topology, TOPOLOGY_SCHEMA, "topology.json")
    
    if not errors:
        errors = _validate_topology_integrity(topology)
    
    return errors

def validate_streams(streams: Dict) -> List[str]:
    """
    Validate the streams.json file.
    
    Args:
        streams: The streams to validate
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    errors = _validate_against_schema(streams, STREAMS_SCHEMA, "streams.json")
    
    if not errors:
        errors = _validate_streams_integrity(streams)
        
    # Check period and deadline based on traffic type
    for stream in streams.get("streams", []):
        stream_type = stream.get("type")
        
        if stream_type == "BEST-EFFORT":
            # BEST-EFFORT should not have period or deadline
            if stream.get("period") is not None:
                errors.append(f"Stream {stream.get('name')} has type BEST-EFFORT, but period should be None.")
            # Check that no destination has a deadline
            for dest in stream.get("destinations", []):
                if dest.get("deadline") is not None:
                    errors.append(f"Stream {stream.get('name')} has type BEST-EFFORT, but destination {dest['id']} has a deadline.")
        elif stream_type == "AUDIO/VOICE":
            # AUDIO/VOICE should not have period, but can have deadline
            if stream.get("period") is not None:
                errors.append(f"Stream {stream.get('name')} has type AUDIO/VOICE, but period should be None.")
            # Check that all destinations have deadlines
            for dest in stream.get("destinations", []):
                if dest.get("deadline") is None:
                    errors.append(f"Stream {stream.get('name')} has type AUDIO/VOICE, but destination {dest['id']} does not have a valid deadline.")
        else:
            # All other traffic types should have period and deadlines
            if stream.get("period") is None:
                errors.append(f"Stream {stream.get('name')} does not have a valid period.")
            # Check that all destinations have deadlines
            for dest in stream.get("destinations", []):
                if dest.get("deadline") is None:
                    errors.append(f"Stream {stream.get('name')} does not have a valid deadline for destination {dest['id']}.")
      
    return errors

def validate_routes(routes: Dict, topology: Dict, streams: Dict) -> List[str]:
    """
    Validate the routes.json file.
    
    Args:
        routes: The routes to validate
        topology: The topology definition
        streams: The streams definition
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    errors = _validate_against_schema(routes, ROUTES_SCHEMA, "routes.json")
    
    if not errors:
        errors = _validate_routes_integrity(routes, topology, streams)
    
    return errors

def _validate_against_schema(data: Dict, schema: Dict, file_name: str) -> List[str]:
    """
    Validate data against a JSON schema.
    
    Args:
        data: The data to validate
        schema: The JSON schema
        file_name: The name of the file being validated
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    errors = []
    
    try:
        jsonschema.validate(data, schema)
    except jsonschema.exceptions.ValidationError as e:
        errors.append(f"Validation error in {file_name}: {e}")
    except Exception as e:
        errors.append(f"Error validating {file_name}: {e}")
    
    return errors

def _validate_topology_integrity(topology: Dict) -> List[str]:
    """
    Validate the integrity of the topology definition.
    
    Args:
        topology: The topology definition
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    errors = []
    
    # Collect all node IDs from both switches and end systems
    node_ids = set()
    for node in topology["topology"].get("switches", []):
        node_ids.add(node["id"])
    for node in topology["topology"].get("end_systems", []):
        node_ids.add(node["id"])
    
    # Check that all nodes referenced in links exist
    for link in topology["topology"].get("links", []):
        if link["source"] not in node_ids:
            errors.append(f"Link {link['id']} references non-existent source node {link['source']}")
        
        if link["destination"] not in node_ids:
            errors.append(f"Link {link['id']} references non-existent destination node {link['destination']}")
    
    # Check that all switches have valid port counts
    for node in topology["topology"].get("switches", []):
        if "ports" not in node:
            errors.append(f"Switch {node['id']} does not have a ports count")
    
    # Check that all links have unique IDs
    link_ids = [link["id"] for link in topology["topology"].get("links", [])]
    if len(link_ids) != len(set(link_ids)):
        errors.append("Duplicate link IDs found in topology")
    
    # Check port counts
    port_usage = {}
    
    for link in topology["topology"].get("links", []):
        source = link["source"]
        source_port = link["sourcePort"]
        
        if source not in port_usage:
            port_usage[source] = {}
        
        port_usage[source][source_port] = port_usage[source].get(source_port, 0) + 1
        
        if port_usage[source][source_port] > 1:
            errors.append(f"Port {source_port} on node {source} is used by multiple links")
    
    return errors

def _validate_streams_integrity(streams: Dict) -> List[str]:
    """
    Validate the integrity of the streams definition.
    
    Args:
        streams: The streams definition
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    errors = []
    
    # Check for duplicate stream IDs
    stream_ids = [stream["id"] for stream in streams["streams"]]
    if len(stream_ids) != len(set(stream_ids)):
        errors.append("Duplicate stream IDs found")
    
    # Check that all streams have valid PCP values
    for stream in streams["streams"]:
        if not 0 <= stream["PCP"] <= 7:
            errors.append(f"Stream {stream['id']} has invalid PCP value {stream['PCP']}")
    
    # Check that all streams have at least one destination
    for stream in streams["streams"]:
        if not stream["destinations"]:
            errors.append(f"Stream {stream['id']} has no destinations")
    
    return errors

def _validate_routes_integrity(routes: Dict, topology: Dict, streams: Dict) -> List[str]:
    """
    Validate the integrity of the routes definition.
    
    Args:
        routes: The routes definition
        topology: The topology definition
        streams: The streams definition
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    errors = []
    
    # Create sets of node IDs by type for quick lookups
    switch_ids = {node["id"] for node in topology["topology"].get("switches", [])}
    end_system_ids = {node["id"] for node in topology["topology"].get("end_systems", [])}
    
    # Create a dictionary of links for quick lookups
    link_dict = {}
    for link in topology["topology"].get("links", []):
        link_dict[(link["source"], link["destination"])] = link
    
    # Check that all streams have routes
    for stream in streams["streams"]:
        stream_id = stream["id"]
        stream_name = stream["name"]
        
        # Find the route for this stream
        route = None
        for r in routes["routes"]:
            if r["flow_id"] == stream_id:
                route = r
                break
        
        if not route:
            errors.append(f"Stream {stream_name} (ID {stream_id}) does not have a route")
            continue
        
        # Check that the route starts at the source and ends at all destinations
        for path in route.get("paths", []):
            if not path:
                errors.append(f"Empty path found for stream {stream_name}")
                continue
            
            source = path[0]["node"]
            if source != stream["source"]:
                errors.append(f"Route for stream {stream_name} does not start at source {stream['source']}")
            
            # Check that each node in the path exists and ports are valid
            prev_node = None
            prev_port = None
            
            for i, hop in enumerate(path):
                node = hop["node"]
                port = hop["port"]
                
                # Check if node exists
                if node not in switch_ids and node not in end_system_ids:
                    errors.append(f"Route for stream {stream_name} references non-existent node {node}")
                    continue
                
                # Check port validity based on node type
                # End systems should use port 0
                is_end_system = node in end_system_ids
                if is_end_system and port != 0:
                    errors.append(f"End system {node} in route for stream {stream_name} uses invalid port {port}, should be 0")
                
                # For switches, check that the port exists
                if not is_end_system:
                    # Find the switch to check its port count
                    switch = next((s for s in topology["topology"].get("switches", []) if s["id"] == node), None)
                    if switch and "ports" in switch and port >= switch["ports"]:
                        errors.append(f"Switch {node} in route for stream {stream_name} uses port {port}, but only has {switch['ports']} ports")
                
                # Check connection to previous hop
                if i > 0 and prev_node:
                    # Check that a link exists between the previous and current node
                    if (prev_node, node) not in link_dict and (node, prev_node) not in link_dict:
                        errors.append(f"No link exists between {prev_node} and {node} in route for stream {stream_name}")
                    
                    # Check that the ports match what's in the topology
                    link = link_dict.get((prev_node, node))
                    if link and link["sourcePort"] != prev_port:
                        errors.append(f"Route for stream {stream_name} uses port {prev_port} on node {prev_node}, but link {link['id']} uses port {link['sourcePort']}")
                    
                    reverse_link = link_dict.get((node, prev_node))
                    if reverse_link and reverse_link["destinationPort"] != prev_port:
                        errors.append(f"Route for stream {stream_name} uses port {prev_port} on node {prev_node}, but link {reverse_link['id']} connects to port {reverse_link['destinationPort']}")
                
                prev_node = node
                prev_port = port
            
            # Check that the last node is one of the destinations
            destination_ids = [dest["id"] for dest in stream["destinations"]]
            if prev_node not in destination_ids:
                errors.append(f"Route path for stream {stream_name} does not end at a destination, ends at {prev_node}")
    
    return errors

def validate_all(topology: Dict, streams: Dict, routes: Optional[Dict] = None) -> List[str]:
    """
    Validate all generated files together.
    
    Args:
        topology: The topology definition
        streams: The streams definition
        routes: The routes definition
        
    Returns:
        List[str]: List of validation errors, or empty list if valid
    """
    errors = []
    
    # Validate each file
    errors.extend(validate_topology(topology))
    errors.extend(validate_streams(streams))
    
    if routes:
        errors.extend(validate_routes(routes, topology, streams))
    
    return errors 