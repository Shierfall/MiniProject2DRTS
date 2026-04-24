"""
route_generator.py

Domain service for generating routes (paths) for streams in a TSN network test case.

This module provides the RouteGenerator class, which computes routing paths for each stream in a generated TSN topology.
It supports shortest-path routing, link utilization tracking, and delay calculation based on traffic type definitions.

Features:
    - Builds a bidirectional network graph from topology data (switches, end systems, links).
    - Generates routes for each stream, supporting redundancy and multicast.
    - Calculates minimum end-to-end delay for each route using log-normal distribution and traffic type constraints.
    - Tracks and updates link utilization if enabled.
    - Validates connectivity and warns about disconnected end systems.

Usage:
    generator = RouteGenerator(topology, streams, traffic_type, traffic_types)
    routes = generator.generate()

Main Class:
    - RouteGenerator: Encapsulates all route generation logic and graph construction.

Raises:
    - SystemExit: For unsupported algorithms or invalid traffic types.
    - Warnings: For missing nodes, links, or paths.
"""
import logging
from typing import Dict, List, Optional
import numpy as np
import sys
import networkx as nx
from tsn_case_gen_.domain.utils_functions import get_delays_from_traffic_type
import os

logger = logging.getLogger(__name__)

class RouteGenerator:
    """Generate routes for streams in TSN test cases."""
    
    def __init__(
        self,
        topology: Dict,
        streams: Dict,
        traffic_type: str,
        traffic_types: List[Dict],
        delay_units: str = "MICRO_SECOND",
        consider_link_utilization: bool = False,
        algorithm: str = "shortest_path"
    ):
        """
        Initialize the route generator.
        
        Args:
            topology: The generated topology
            streams: The generated streams
            traffic_type: Name of the specific traffic type
            traffic_types: List of traffic type definitions from the configuration
            delay_units: Units for delay values
            consider_link_utilization: Whether to consider link utilization when computing routes
            algorithm: Routing algorithm to use ("shortest_path" supported)
        """
        # Initialize parameters
        self.topology = topology
        self.streams = streams
        self.delay_units = delay_units
        self.traffic_type = traffic_type
        self.traffic_types = traffic_types
        self.consider_link_utilization = consider_link_utilization
        self.algorithm = algorithm

        # Validate algorithm
        if self.algorithm != "shortest_path":
            logger.error(f"Unsupported routing algorithm: {self.algorithm}")
            sys.exit(1)
        
        # Build graph from topology
        self.graph = self._build_graph()
        
        # Track link utilization
        self.link_utilization = {}
        self.used_port_pairs = {}
    
    def _build_graph(self) -> nx.Graph:
        """
        Build an undirected graph from the topology.
        
        Returns:
            nx.Graph: The undirected graph representing the network
        """
        # Use undirected graph for route finding to ensure bidirectionality
        G = nx.Graph()
        
        # Add switches to the graph
        for node in self.topology.get("switches", []):
            node_data = node.copy()
            node_data["type"] = "switch"
            G.add_node(node["id"], **node_data)
        
        # Add end systems to the graph
        for node in self.topology.get("end_systems", []):
            node_data = node.copy()
            node_data["type"] = "end_system"
            G.add_node(node["id"], **node_data)
        
        # Track processed links to avoid duplicates
        processed_links = set()
        
        # Add edges to the graph
        for link in self.topology.get("links", []):
            source = link["source"]
            dest = link["destination"]
            link_key = tuple(sorted([source, dest]))
            
            # Skip if we've already processed this link
            if link_key in processed_links:
                continue
            
            # Create a lightweight representation of the link for the graph
            link_data = {
                "link_id": link["id"],
                "sourcePort": link["sourcePort"],
                "destinationPort": link["destinationPort"],
                "bandwidth_mbps": link.get("bandwidth_mbps", self.topology.get("default_bandwidth_mbps", 1000)),
                "utilization": 0.0
            }
            
            # Add the undirected edge
            G.add_edge(source, dest, **link_data)
            processed_links.add(link_key)
        
        # Verify connectivity between end systems
        end_systems = [n for n in G.nodes() if G.nodes[n].get("type") == "end_system"]
        disconnected_pairs = []
        
        for i, source in enumerate(end_systems):
            for dest in end_systems[i+1:]:
                if not nx.has_path(G, source, dest):
                    disconnected_pairs.append((source, dest))
        
        if disconnected_pairs:
            logger.warning(f"Found {len(disconnected_pairs)} disconnected end system pairs")
            for pair in disconnected_pairs:
                logger.warning(f"No path exists between {pair[0]} and {pair[1]}")
        else:
            logger.info("All end systems are connected - topology is fully routable")
        
        return G
    
    def generate(self) -> Dict:
        """
        Generate routes for all streams.
        
        Returns:
            Dict: The complete routes definition
        """
        # Initialize routes structure
        routes_def = {
            "delay_units": self.delay_units,
            "routes": []
        }
        
        # Generate routes for each stream
        for stream in self.streams["streams"]:
            route = self._generate_route_for_stream(stream)
            
            if route:
                routes_def["routes"].append(route)
        
        logger.info(f"Generated routes for {len(routes_def['routes'])} streams")
        
        return routes_def
    
    def _generate_route_for_stream(self, stream: Dict) -> Optional[Dict]:
        """
        Generate a route for a specific stream.
        
        Args:
            stream: The stream definition
            
        Returns:
            Optional[Dict]: The route definition, or None if no route could be found
        """
        source = stream["source"]
        destinations = stream["destinations"]
        redundancy = stream.get("redundancy", 0)
        
        # Check if source and all destinations exist in the graph
        if source not in self.graph:
            logger.warning(f"Source node {source} not found in topology. Skipping route generation.")
            return None
        
        for dest in destinations:
            if dest["id"] not in self.graph:
                logger.warning(f"Destination node {dest} not found in topology. Skipping route generation.")
                return None
        
        # Track paths for multicast
        all_paths = []
        
        # Find path(s) to each destination
        for dest in destinations:
            paths = self._find_paths(source, dest["id"], redundancy + 1)
            
            if not paths:
                logger.warning(f"No path found from {source} to {dest['id']}. Skipping route generation.")
                return None
            
            all_paths.extend(paths)
            
        traffic_type = stream.get("type", None)
        deadline = stream.get("deadline", None)
        
        # Create the route definition
        route = {
            "flow_id": stream["id"],
            "paths": [],
            "min_e2e_delay": self._calculate_min_e2e_delay(all_paths[0], traffic_type, deadline)  # Use the first path
        }
        
        # Add path details - convert undirected paths to directed paths
        for path in all_paths:
            route_path = []
            
            for i, node_id in enumerate(path):
                # When constructing the directed path, we need to look up port information
                # from the appropriate link in the topology
                if i < len(path) - 1:
                    # Find the matching link in the topology
                    next_node = path[i + 1]
                    link = self._find_link(node_id, next_node)
                    
                    if link:
                        port = link["sourcePort"]
                    else:
                        logger.warning(f"Missing link {node_id} → {next_node} in topology")
                        port = 0
                else:
                    # For end systems, always use port 0
                    port = 0
                
                route_path.append({
                    "node": node_id,
                    "port": port
                })
            
            route["paths"].append(route_path)
        
        # Update link utilization if enabled
        self._update_link_utilization(all_paths, stream)
        
        return route
    
    def _find_paths(self, source: str, dest: str, num_paths: int) -> List[List[str]]:
        """
        Find multiple paths from source to destination.
        
        Args:
            source: The source node ID
            dest: The destination node ID
            num_paths: Number of paths to find
            
        Returns:
            List[List[str]]: List of paths, where each path is a list of node IDs
        """
        # Only shortest_path is supported for now
        if self.algorithm == "shortest_path":
            paths = []
            # First check if a path exists at all
            if not nx.has_path(self.graph, source, dest):
                logger.warning(f"No path exists from {source} to {dest} in the graph")
                return []
            
            # Define optional weight function for link utilization
            weight = None
            if self.consider_link_utilization:
                def weight_function(u, v, data):
                    return 1.0 + data.get("utilization", 0.0)
                weight = weight_function

            # First path is always the (weighted) shortest path
            try:
                first_path = nx.shortest_path(self.graph, source, dest, weight=weight)
                paths.append(first_path)
            except nx.NetworkXNoPath:
                logger.warning(f"No path found from {source} to {dest}")
                return []

            if num_paths <= 1:
                return paths

            # Create a copy of the graph for path finding
            G = self.graph.copy()
            
            # Try to find additional paths by temporarily increasing weights of used edges
            for _ in range(num_paths - 1):
                temp_G = G.copy()
                
                for path in paths:
                    for i in range(len(path) - 1):
                        if temp_G.has_edge(path[i], path[i + 1]):
                            current_weight = temp_G[path[i]][path[i + 1]].get('weight', 1.0)
                            temp_G[path[i]][path[i + 1]]['weight'] = current_weight * 2.0
                
                try:
                    # Try to find a new path with the modified weights
                    new_path = nx.shortest_path(temp_G, source, dest, weight='weight')
                    if new_path not in paths:
                        paths.append(new_path)
                        if len(paths) >= num_paths:
                            break
                except nx.NetworkXNoPath:
                    logger.warning(f"Could not find additional path from {source} to {dest}")
                    break

            if len(paths) < num_paths:
                logger.warning(f"Could only find {len(paths)} paths out of {num_paths} requested for {source} to {dest}")

            return paths[:num_paths]
        else:
            logger.error(f"Routing algorithm '{self.algorithm}' is not implemented.")
            sys.exit(1)
    
    def _update_link_utilization(self, paths: List[List[str]], stream: Dict) -> None:
        """
        Update link utilization based on the stream's paths.
        
        Args:
            paths: List of paths, where each path is a list of node IDs
            stream: The stream definition
        """
        if not self.consider_link_utilization:
            return
        
        # Skip link utilization calculation for streams without period (BEST-EFFORT and AUDIO/VOICE)
        if stream.get("period") is None:
            return
        
        # Calculate stream bandwidth requirement
        packet_size_bits = stream["size"] * 8
        period_seconds = stream["period"] /1e6
        bandwidth_bps = packet_size_bits / period_seconds
        
        # Update utilization for each link in the paths
        for path in paths:
            for i in range(len(path) - 1):
                edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                link_id = edge_data["link_id"]
                link_bandwidth_bps = edge_data["bandwidth_mbps"] * 1e6
                
                # Calculate utilization percentage for this stream on this link
                stream_utilization = (bandwidth_bps / link_bandwidth_bps) * 100.0
                
                # Update total link utilization
                current_utilization = edge_data.get("utilization", 0.0)
                new_utilization = current_utilization + stream_utilization
                
                # Cap utilization at 100%
                edge_data["utilization"] = min(new_utilization, 100.0)
                
                # Store utilization for reference
                self.link_utilization[link_id] = edge_data["utilization"]
    
    def _calculate_min_e2e_delay(self, path: List[str], traffic_type: str, deadline: float = None) -> float:
        """
        Calculate the minimum end-to-end delay for a path.
        
        Args:
            path: The path as a list of node IDs
            traffic_type: The traffic type name
            deadline: The deadline for the stream (optional)
        
        Returns:
            float: The minimum end-to-end delay in microseconds
        """
        
        # No delay for BEST-EFFORT traffic
        if traffic_type == "BEST-EFFORT":
            return 0.0
        
        # Get delays from the traffic type
        result = get_delays_from_traffic_type(traffic_type, self.traffic_types)

        if result is None:
            logger.error(f"Invalid traffic type: {traffic_type}")
            raise ValueError(f"Invalid traffic type: {traffic_type}")

        stream_min_delay, stream_max_delay = result

        # Check if delays are set (shouldn't be necessary after the above check, but just in case)
        if stream_min_delay is None or stream_max_delay is None:
            logger.error("Stream delays 'min_delay' and 'max_delay' must be set")
            raise ValueError("Stream delays 'min_delay' and 'max_delay' must be set")
                
        # Number of hops = number of links = number of nodes - 1
        num_hops = len(path) - 1
        
        # Calculate the mean and standard deviation of the delays
        mean_delay = np.mean([stream_min_delay, stream_max_delay])
        std_dev = np.std([stream_min_delay, stream_max_delay])
        
        # Generate a random delay using log-normal distribution
        random_delay = np.random.lognormal(np.log(mean_delay), std_dev)
        
        # Clip the delay to the min and max values
        clipped_delay = np.clip(random_delay, stream_min_delay, stream_max_delay)
        
        total_delay = clipped_delay * num_hops
        # Cap the delay to the deadline if provided
        if deadline is not None:
            total_delay = min(total_delay, deadline)
        return total_delay 
    
    def _find_link(self, source: str, dest: str) -> Optional[Dict]:
        """
        Find a link between two nodes in the topology.
        
        Args:
            source: The source node ID
            dest: The destination node ID
            
        Returns:
            Optional[Dict]: The link data, or None if no link was found
        """
        for link in self.topology["links"]:
            if link["source"] == source and link["destination"] == dest:
                return link
        return None

validation_script = os.path.join(os.path.dirname(__file__), '../domain/validation.py')