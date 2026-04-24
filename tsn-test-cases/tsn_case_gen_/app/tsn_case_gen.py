"""
tsn_case_gen.py

Main domain entry point for generating TSN test cases from a configuration file.

This module provides the TSNTestCaseGenerator class, which orchestrates the generation of topology, streams, and routes for Time-Sensitive Networks (TSN).
It validates configuration, manages output directories, and writes all generated files according to project specifications.

Features:
    - Loads and validates configuration from gen_config.json using schema validation.
    - Generates network topology, streams, and routes using dedicated domain services.
    - Supports multi-domain topologies, cross-domain streams, and configurable routing algorithms.
    - Writes output files (topology.json, streams.json, routes.json) in the specified directory.
    - Provides CLI entry point for batch test case generation with reproducibility and verbose logging.

Usage:
    python tsn_case_gen.py --config=gen_config.json [--seed=123] [--verbose]

Main Class:
    - TSNTestCaseGenerator: Orchestrates all test case generation steps and file outputs.

Main Functions:
    - main: CLI entry point for running the generator.

Raises:
    - ValueError: For invalid configuration or file I/O errors.
    - SystemExit: For unrecoverable errors in CLI usage or generation.
"""

import argparse
import json
import logging
import os
import random
import sys
import numpy as np
from typing import Dict, Optional
from tsn_case_gen_.domain.topology_generator import TopologyGenerator
from tsn_case_gen_.domain.stream_generator import StreamGenerator
from tsn_case_gen_.domain.route_generator import RouteGenerator
from tsn_case_gen_.domain.test_case_validation import validate_gen_config, validate_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class TSNTestCaseGenerator:
    """Main class for generating TSN test cases."""
    
    def __init__(self, config_path: str, seed: Optional[int] = None, verbose: bool = False):
        """
        Initialize the TSN test case generator.
        
        Args:
            config_path: Path to the chosen *_config file
            seed: Random seed for reproducibility
            verbose: Whether to enable verbose logging
        """
    
        self.config_path = config_path
        self.seed = seed

        # Set logging level
        if verbose:
            logger.setLevel(logging.DEBUG)

        # Initialize random number generator
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            logger.info(f"Random seed set to {seed}")

        # Load and validate configuration
        self.config = self.load_config()

        # Extract basic parameters
        self.delay_units = self.config.get("delay_units", "MICRO_SECOND")
        self.num_test_cases = self.config["general"]["num_test_cases"]
        self.num_domains = self.config["general"].get("num_domains", 1)
        self.output_directory = self.config["general"]["output_directory"]
        self.cross_domain_streams = self.config["general"].get("cross_domain_streams", 0)
        self.should_generate_routes = self.config["general"].get("generate_routes", True)

        # Extract topology configuration
        topology_config = self.config.get("network", {})
        self.topology_type = topology_config.get("topology_type", "mesh_graph")
        self.topology_params = topology_config.get("parameters", "{}")
        self.default_bandwidth_mbps = topology_config.get("default_bandwidth_mbps", 1000)

        # Extract network constraints
        network_constraints = topology_config.get("constraints", {})
        self.max_path_length = network_constraints.get("max_path_length")
        self.min_redundant_paths = network_constraints.get("min_redundant_paths", 1)

        # Extract domain connection configuration
        domain_config = self.config.get("domain_connections", {})
        self.domain_connection_type = domain_config.get("type")
        self.connections_per_domain_pair = domain_config.get("connections_per_domain_pair", 1)

        # Create output directory if it doesn't exist
        os.makedirs(self.output_directory, exist_ok=True)
        
    def load_config(self) -> Dict:
        """
        Load and validate the gen_config.json file.
        
        Returns:
            Dict: The loaded configuration
        
        Raises:
            ValueError: If the configuration is invalid
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Validate against schema
            errors = validate_gen_config(config)
            if errors:
                for error in errors:
                    logger.error(error)
                raise ValueError("Invalid configuration")

            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def generate_test_cases(self):
        """Generate all test cases based on the configuration."""
        logger.info(f"Generating {self.num_test_cases} test cases...")

        # Get test case naming pattern from config or use default
        naming_pattern = self.config.get("general", {}).get("test_case_naming", "test_case_{}")

        for i in range(self.num_test_cases):
            test_case_id = naming_pattern.format(i+1)
            logger.info(f"Generating test case {test_case_id}")

            # Create test case directory
            test_case_dir = os.path.join(self.output_directory, test_case_id)
            os.makedirs(test_case_dir, exist_ok=True)

            # Generate topology
            topology = self.generate_topology()

            # Generate streams
            streams = self.generate_streams(topology)

            # Generate routes if enabled
            routes = None
            if self.should_generate_routes:
                routes = self.generate_routes(topology, streams)

            # Validate the generated files
            errors = validate_all({"topology": topology}, streams, routes)
            if errors:
                logger.warning("Validation errors found:")
                for error in errors:
                    logger.warning(f"  {error}")

            # Write output files
            self.write_topology(topology, test_case_dir)
            self.write_streams(streams, test_case_dir)
            if routes:
                self.write_routes(routes, test_case_dir)

            logger.info(f"Test case {test_case_id} generated successfully")
    
    def generate_topology(self) -> Dict:
        """
        Generate the network topology.
        
        Returns:
            Dict: The topology definition
        """
        logger.debug("Generating topology...")

        # Create topology generator
        topology_generator = TopologyGenerator(
            num_domains=self.num_domains,
            topology_type=self.topology_type,
            num_switches=self.config["general"]["topology_size"]["num_switches"],
            num_end_systems=self.config["general"]["topology_size"]["num_end_systems"],
            end_systems_per_switch=self.config["general"]["topology_size"]["end_systems_per_switch"],
            topology_params=self.topology_params,
            domain_connection_type=self.domain_connection_type,
            connections_per_domain_pair=self.connections_per_domain_pair,
            delay_units=self.delay_units,
            default_bandwidth_mbps=self.default_bandwidth_mbps,
            max_path_length=self.max_path_length,
            min_redundant_paths=self.min_redundant_paths
        )

        # Generate topology
        return topology_generator.generate()
    
    def generate_streams(self, topology: Dict) -> Dict:
        """
        Generate the network streams based on the topology.
        
        Args:
            topology: The generated topology
            
        Returns:
            Dict: The streams definition
        """
        logger.debug("Generating streams...")

        # Extract traffic configuration
        traffic_types = self.config["traffic"]["types"]

        # Create stream generator
        stream_generator = StreamGenerator(
            topology=topology,
            traffic_types=traffic_types,
            delay_units=self.delay_units,
            num_domains=self.num_domains,
            cross_domain_streams=self.cross_domain_streams
        )

        # Generate streams
        return stream_generator.generate()
    
    def generate_routes(self, topology: Dict, streams: Dict) -> Dict:
        """
        Generate routes for streams.
        
        Args:
            topology: The generated topology
            streams: The generated streams
            
        Returns:
            Dict: The routes definition
        """
        logger.debug("Generating routes...")

        # Extract routing configuration
        routing_config = self.config.get("routing", {})
        consider_link_utilization = routing_config.get("consider_link_utilization", False)
        algorithm = routing_config.get("algorithm", "shortest_path")

        # Extract traffic configuration
        traffic_types = self.config["traffic"]["types"]

        # Create route generator
        route_generator = RouteGenerator(
            topology=topology,
            streams=streams,
            traffic_type=traffic_types,
            traffic_types=traffic_types,
            delay_units=self.delay_units,
            consider_link_utilization=consider_link_utilization,
            algorithm=algorithm,
        )

        # Generate routes
        return route_generator.generate()
    
    def write_topology(self, topology: Dict, output_dir: str):
        """
        Write the topology to a JSON file.
        
        Args:
            topology: The topology definition
            output_dir: The output directory
        """
        output_path = os.path.join(output_dir, "topology.json")

        # Write to file with comments
        with open(output_path, 'w') as f:
            f.write("{\n")

            # Write the actual topology data
            topology_json = json.dumps({"topology": topology}, indent=2)
            topology_json = topology_json[1:-1].strip()

            f.write(topology_json)
            f.write("\n}")

        logger.debug(f"Topology written to {output_path}")
    
    def write_streams(self, streams: Dict, output_dir: str):
        """
        Write the streams to a JSON file.
        
        Args:
            streams: The streams definition
            output_dir: The output directory
        """
        output_path = os.path.join(output_dir, "streams.json")

        # Write to file with comments
        with open(output_path, 'w') as f:
            f.write("{\n")

            # Write the delay_units field
            f.write(f'  "delay_units": "{streams["delay_units"]}",\n')

            # Write the streams array with a comment
            f.write('  "streams": [\n')

            # Write each stream
            for i, stream in enumerate(streams["streams"]):
                stream_json = json.dumps(stream, indent=4)
                stream_json = stream_json.replace("\n", "\n    ")

                f.write("    " + stream_json)

                if i < len(streams["streams"]) - 1:
                    f.write(",\n")
                else:
                    f.write("\n")

            f.write("  ]\n}")

        logger.debug(f"Streams written to {output_path}")
    
    def write_routes(self, routes: Dict, output_dir: str):
        """
        Write the routes to a JSON file.
        
        Args:
            routes: The routes definition
            output_dir: The output directory
        """
        output_path = os.path.join(output_dir, "routes.json")

        # Write to file with comments
        with open(output_path, 'w') as f:
            f.write("{\n")

            # Write the delay_units field
            f.write(f'  "delay_units": "{routes["delay_units"]}",\n')

            # Write the routes array with a comment
            f.write('  "routes": [\n')

            # Write each route
            for i, route in enumerate(routes["routes"]):
                route_json = json.dumps(route, indent=4)
                route_json = route_json.replace("\n", "\n    ")

                f.write("    " + route_json)

                if i < len(routes["routes"]) - 1:
                    f.write(",\n")
                else:
                    f.write("\n")

            f.write("  ]\n}")

        logger.debug(f"Routes written to {output_path}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='TSN Test Case Generator')
    parser.add_argument('--config', type=str, help='Path to gen_config.json (defaults to ./industrial_config.json if not specified)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # If config is not specified, use default gen_config.json in the current directory
    if args.config is None:
        default_config = 'industrial_config.json'
        if os.path.exists(default_config):
            logger.info(f"No config specified, using industrial config file: {default_config}")
            args.config = default_config
        else:
            logger.error(f"No config specified and industrial config file '{default_config}' not found.")
            logger.error("Please provide a config file with --config or create a new one in the current directory.")
            sys.exit(1)
    
    try:
        # Initialize and run the generator
        generator = TSNTestCaseGenerator(args.config, args.seed, args.verbose)
        generator.generate_test_cases()
        logger.info("Test case generation completed successfully")
    except Exception as e:
        logger.error(f"Error generating test cases: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 