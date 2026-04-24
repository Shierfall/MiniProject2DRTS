"""
topology_generator.py

Domain service for generating network topologies for TSN test cases.

This module provides the TopologyGenerator class, which creates topologies for single- and multi-domain TSN networks.
It supports various topology types (mesh, binomial, ring, tree, random geometric), domain interconnection strategies, and realistic link properties.

Features:
    - Generates topologies with switches, end systems, and links, supporting multiple domains.
    - Supports mesh, binomial, industrial ring, tree, and random geometric graphs using NetworkX.
    - Assigns realistic bandwidth and delay properties to links based on connection type.
    - Connects domains using line, square, or random strategies, with configurable connections per domain pair.
    - Smart port management for switches to avoid port conflicts.
    - Validates topology parameters and warns about configuration mismatches.

Usage:
    generator = TopologyGenerator(...)
    topology = generator.generate()

Main Class:
    - TopologyGenerator: Encapsulates all topology generation logic and domain knowledge.

Raises:
    - SystemExit: For missing or invalid topology parameters, or port exhaustion.
    - Warnings: For configuration mismatches or insufficient resources.
"""
import logging
import ast
import random
import sys
from typing import Dict, List, Optional
import networkx as nx

logger = logging.getLogger(__name__)

class TopologyGenerator:
    """Generate network topologies for TSN test cases."""
    
    def __init__(
        self,
        num_domains: int,
        topology_type: str, 
        num_switches: int,
        num_end_systems: int,
        end_systems_per_switch: List[int],
        topology_params: str,
        domain_connection_type: Optional[str] = None,
        connections_per_domain_pair: Optional[int] = None,
        delay_units: str = "MICRO_SECOND",
        default_bandwidth_mbps: int = 1000,
        max_path_length: Optional[int] = None,
        min_redundant_paths: int = 1
    ):
        """
        Initialize the topology generator.
        
        Args:
            num_domains: Number of TSN domains
            topology_type: Type of topology to generate (e.g., "mesh_graph", "industrial_ring_topology")
            topology_params: Parameters for the topology generator as a JSON string
            num_switches: Number of switches per domain
            num_end_systems: Number of end systems per domain
            end_systems_per_switch: Number of end systems per switch
            domain_connection_type: How domains are connected (e.g., "line", "square")
            connections_per_domain_pair: Number of connections between each connected domain pair
            delay_units: Units for delay values
            default_bandwidth_mbps: Default bandwidth for links in Mbps (used if link_bandwidth_range is None)
            max_path_length: Maximum allowed path length between any two nodes
            min_redundant_paths: Minimum number of independent paths required between critical nodes
        """
        self.num_domains = num_domains
        self.topology_type = topology_type
        self.topology_params = topology_params
        self.num_switches = num_switches
        self.num_end_systems = num_end_systems
        self.end_systems_per_switch = end_systems_per_switch
        self.domain_connection_type = domain_connection_type
        self.connections_per_domain_pair = connections_per_domain_pair
        self.delay_units = delay_units
        self.default_bandwidth_mbps = default_bandwidth_mbps
        self.max_path_length = max_path_length
        self.min_redundant_paths = min_redundant_paths
        
        # Initialize counters for unique IDs
        self.switch_counter = 0
        self.node_counter = 0
        self.link_counter = 0
        
        # Track switch port usage
        self.used_ports = {}  # switch_id -> set of used ports
        
        # To store domain graphs for reference
        self.domain_graphs = []
        
    def _parse_params(self, params_str: str) -> Dict:
        """
        Parse the topology parameters string into a Python dictionary.
        
        Args:
            params_str: The parameters string from gen_config.json
            
        Returns:
            Dict: The parsed parameters
        """
        try:
            return ast.literal_eval(params_str)
        except (ValueError, SyntaxError) as e:
            logger.error(f"Error parsing topology parameters: {e}")
            return {}
    
    def _generate_link_properties(self, source: str, dest: str, connection_type: str = "default") -> Dict[str, float]:
        """
        Generate link properties (bandwidth and delay) based on link type and position.
        
        Args:
            source: Source node ID
            dest: Destination node ID
            connection_type: Type of connection ("switch_to_switch", "switch_to_end_system", "domain_connection")
            
        Returns:
            Dict[str, float]: Dictionary containing bandwidth_mbps and delay values
        """
        properties = {}
        
        # Determine bandwidth based on connection type and position
        if connection_type == "domain_connection":
            # Inter-domain links get highest bandwidth (10 Gbps)
            properties["bandwidth_mbps"] = 10000
        elif connection_type == "switch_to_switch":
            # Core/distribution links get 1 Gbps
            properties["bandwidth_mbps"] = 1000
        else:
            # Access links (to end systems) get 100 Mbps
            properties["bandwidth_mbps"] = 100
        
        # Determine delay based on connection type and physical characteristics
        if connection_type == "domain_connection":
            # Inter-domain links have higher delay due to longer distances
            properties["delay"] = round(random.uniform(50, 100), 3)
        elif connection_type == "switch_to_switch":
            # Core/distribution links have medium delay
            properties["delay"] = round(random.uniform(10, 50), 3)
        else:
            # Access links have lowest delay
            properties["delay"] = round(random.uniform(1, 10), 3)
        
        return properties

    def generate(self) -> Dict:
        """
        Generate the network topology.
        
        Returns:
            Dict: The topology definition
        """
        # Initialize the topology structure
        topology = {
            "delay_units": self.delay_units,
            "default_bandwidth_mbps": self.default_bandwidth_mbps,
            "switches": [],
            "end_systems": [],
            "links": []
        }
        
        # Reset domain graphs
        self.domain_graphs = []
        
        # Generate domain graphs
        for domain_id in range(self.num_domains):
            domain_graph = self._generate_domain_graph(domain_id)
            self.domain_graphs.append(domain_graph)
            
            # Add nodes from this domain to the topology, separating by type
            for node_id, node_data in domain_graph.nodes(data=True):
                # Create a copy of node data without the 'type' field
                node_entry = {k: v for k, v in node_data.items() if k != 'type'}
                
                # Add to correct array based on type
                if node_data.get('type') == 'switch':
                    topology["switches"].append(node_entry)
                elif node_data.get('type') == 'end_system':
                    topology["end_systems"].append(node_entry)
        
        # Reset link counter
        self.link_counter = 0
        
        # Process each domain graph for links
        for graph in self.domain_graphs:
            for u, v, data in graph.edges(data=True):
                # Generate link properties
                link_properties = self._generate_link_properties(u, v, data.get('connection_type', 'default'))
                
                # Create forward link with new naming
                forward_link = {
                    "id": f"Link{self.link_counter}",
                    "source": u,
                    "destination": v,
                    "sourcePort": data.get('source_port', 0),
                    "destinationPort": data.get('dest_port', 0),
                    "domain": self._get_node_domain(u),
                    **link_properties
                }
                self.link_counter += 1
                topology["links"].append(forward_link)
                
                # Create reverse link with new naming
                reverse_link = {
                    "id": f"Link{self.link_counter}",
                    "source": v,
                    "destination": u,
                    "sourcePort": data.get('dest_port', 0),
                    "destinationPort": data.get('source_port', 0),
                    "domain": self._get_node_domain(v),
                    **link_properties
                }
                self.link_counter += 1
                topology["links"].append(reverse_link)
        
        # Connect domains if needed
        if self.num_domains > 1 and self.domain_connection_type:
            self._connect_domains(self.domain_graphs, topology)
        
        logger.info(f"Generated topology with {len(topology['switches']) + len(topology['end_systems'])} nodes and {len(topology['links'])} links")
        
        return topology
    
    def _generate_domain_graph(self, domain_id: int) -> nx.Graph:
        """
        Generate the graph for a single domain.
        
        Args:
            domain_id: The ID of the domain
            
        Returns:
            nx.Graph: The domain graph with nodes and edges
        """
        # Create a new graph - keep it undirected for consistency
        G = nx.Graph()
        
        # Generate the base graph based on the topology type
        if self.topology_type == "mesh_graph":
            base_graph = self._generate_mesh_graph()
        elif self.topology_type == "binomial_graph":
            base_graph = self._generate_binomial_graph()
        elif self.topology_type == "industrial_ring_graph":
            base_graph = self._generate_industrial_ring()
        elif self.topology_type == "random_geometric_graph":
            base_graph = self._generate_random_geometric_graph()
        elif self.topology_type == "tree_graph":
            base_graph = self._generate_tree_graph()
        else:
            logger.warning(f"Unknown topology type: {self.topology_type}. Defaulting to mesh graph.")
            base_graph = self._generate_mesh_graph()
        
        # Create a mapping for node indices
        node_to_index = {node: i for i, node in enumerate(base_graph.nodes())}
        
        # Add switches to the graph
        for i, node in enumerate(base_graph.nodes()):
            switch_id = f"SW{self.switch_counter}"
            self.switch_counter += 1
            
            # Create switch with specified number of ports and domain ID
            switch_data = {
                "id": switch_id,
                "type": "switch",
                "ports": 8, 
                "domain": domain_id 
            }
            
            G.add_node(switch_id, **switch_data)
            self.used_ports[switch_id] = set()
        
        # Collect all switches
        switches = [n for n in G.nodes() if G.nodes[n].get("type") == "switch"]
        
        # Connect switches based on the base graph edges
        for i, (u, v) in enumerate(base_graph.edges()):
            # Convert graph nodes to indices properly
            u_idx = node_to_index[u]
            v_idx = node_to_index[v]
            
            if u_idx < len(switches) and v_idx < len(switches):
                source = switches[u_idx]
                dest = switches[v_idx]
                
                # Simply add an undirected edge to maintain topology
                G.add_edge(source, dest)
                
                # Track ports for later use in the bidirectional link creation
                source_port = self._get_next_port(source, "switch_to_switch")
                dest_port = self._get_next_port(dest, "switch_to_switch")
                
                G.edges[source, dest]['source_port'] = source_port
                G.edges[source, dest]['dest_port'] = dest_port
                G.edges[source, dest]['connection_type'] = "switch_to_switch"
                
                # Update used ports
                self.used_ports[source].add(source_port)
                self.used_ports[dest].add(dest_port)
        
        # Add end systems to each switch
        remaining_end_systems = self.num_end_systems
        switches = [n for n in G.nodes() if G.nodes[n].get("type") == "switch"]
        
        switch_end_system_counts = {switch_id: 0 for switch_id in switches}
        
        # Distribute end systems randomly while respecting constraints
        while remaining_end_systems > 0:
            available_switches = [s for s in switches if switch_end_system_counts[s] < 4]
            
            if not available_switches:
                logger.warning("Could not distribute all end systems due to switch capacity constraints")
                break

            # Randomly selects a switch and adds end_system 
            selected_switch = random.choice(available_switches)

            node_id = f"ES{self.node_counter}"
            self.node_counter += 1
            
            end_system_data = {
                "id": node_id,
                "type": "end_system",
                "domain": domain_id
            }
            
            G.add_node(node_id, **end_system_data)
            
            source_port = self._get_next_port(selected_switch, "switch_to_end_system")
            G.add_edge(selected_switch, node_id)
            G.edges[selected_switch, node_id]['source_port'] = source_port
            G.edges[selected_switch, node_id]['dest_port'] = 0
            G.edges[selected_switch, node_id]['connection_type'] = "switch_to_end_system"
            
            switch_end_system_counts[selected_switch] += 1
            remaining_end_systems -= 1
            self.used_ports[selected_switch].add(source_port)
        
        return G
    
    def _generate_mesh_graph(self) -> nx.Graph:
        """
        Generate a mesh graph using NetworkX.
        
        Returns:
            nx.Graph: The generated mesh graph
        """
        
        if self.topology_params:
            param = self._parse_params(self.topology_params)
            n = param.get('n')
            m = param.get('m')
            if n is None or m is None:
                logger.error(f"Missing parameters 'n' or 'm' for {self.topology_type}")
                sys.exit(1)
        else:
            logger.error(f"Missing topology parameters for {self.topology_type}")
            sys.exit(1)

        total_positions = n * m
        
        # Validate that the mesh size matches the number of switches
        if total_positions < self.num_switches:
            logger.error(
                f"Mesh graph size ({n}x{m}={total_positions} positions) is smaller than "
                f"requested number of switches ({self.num_switches}). Please adjust either "
                f"the mesh parameters or the number of switches."
            )
            sys.exit(1)
        elif total_positions > self.num_switches:
            logger.error(
                f"Mesh graph size ({n}x{m}={total_positions} positions) is larger than "
                f"requested number of switches ({self.num_switches}). Please adjust either "
                f"the mesh parameters or the number of switches to match."
            )
            sys.exit(1)

        return nx.grid_2d_graph(n, m)
    
    def _generate_binomial_graph(self) -> nx.Graph:
        """
        Generate a binomial graph using NetworkX.
        
        Returns:
            nx.Graph: The generated binomial graph

        """
        if self.topology_params:
            param = self._parse_params(self.topology_params)
            p = param.get('p')
            if p is None:
                logger.error(f"Parameter p is not set for {self.topology_type}")
                sys.exit(1)
        else:
            logger.error(f"Missing topology parameters for {self.topology_type}")
            sys.exit(1)
            
        return nx.gnp_random_graph(self.num_switches, p)
    
    def _generate_random_geometric_graph(self) -> nx.Graph:
        """
        Generate a random geometric graph using NetworkX.
        
        Returns:
            nx.Graph: The generated random geometric graph
            
        """
        if self.topology_params:
            param = self._parse_params(self.topology_params)
            try:
                r = param.get('r')
                if r is None:
                    logger.error(f"Parameter r is not set for {self.topology_type}")
                    sys.exit(1)
                return nx.random_geometric_graph(self.num_switches, r)
            except Exception:
                logger.error(f"Parameter r is not set for {self.topology_type}")
                sys.exit(1)
        else:
            logger.error(f"Parameter not set for {self.topology_type}")
            sys.exit(1)
    
    def _generate_industrial_ring(self) -> nx.Graph:
        """
        Generate a custom industrial ring topology.
        
        Returns:
            nx.Graph: The generated industrial ring graph
        """
        G = nx.Graph()
        if self.topology_params:
            param = self._parse_params(self.topology_params)
            num_rings = param.get('cwsg_num_rings')
            if num_rings is None:
                logger.error(f"Parameter cwsg_num_rings is not set for {self.topology_type}")
                sys.exit(1)
        else:
            logger.error(f"Parameter cwsg_num_rings is not set for {self.topology_type}")
            sys.exit(1)
        
        # Calculate nodes per ring
        nodes_per_ring = max(3, self.num_switches // num_rings)
        total_nodes = nodes_per_ring * num_rings
        
        # Validate that the ring configuration matches the number of switches
        if total_nodes < self.num_switches:
            logger.error(
                f"Industrial ring configuration ({num_rings} rings with {nodes_per_ring} nodes each = {total_nodes} positions) "
                f"is smaller than requested number of switches ({self.num_switches}). Please adjust either "
                f"the number of rings or the number of switches."
            )
            sys.exit(1)
        elif total_nodes > self.num_switches:
            logger.error(
                f"Industrial ring configuration ({num_rings} rings with {nodes_per_ring} nodes each = {total_nodes} positions) "
                f"is larger than requested number of switches ({self.num_switches}). Please adjust either "
                f"the number of rings or the number of switches to match."
            )
            sys.exit(1)
        
        # Create nodes (numbered 0 to num_switches-1)
        for i in range(self.num_switches):
            G.add_node(i)
        
        # Create rings
        for ring in range(num_rings):
            ring_start = ring * nodes_per_ring
            ring_end = min((ring + 1) * nodes_per_ring - 1, self.num_switches - 1)
            
            # Connect nodes in a ring
            for i in range(ring_start, ring_end):
                G.add_edge(i, i + 1)
            
            # Close the ring
            if ring_end > ring_start:
                G.add_edge(ring_end, ring_start)
        
        # Interconnect rings if there are multiple rings
        if num_rings > 1:
            for ring in range(num_rings - 1):
                # Connect a random node from this ring to a random node from the next ring
                source_candidates = list(range(ring * nodes_per_ring, (ring + 1) * nodes_per_ring))
                target_candidates = list(range((ring + 1) * nodes_per_ring, (ring + 2) * nodes_per_ring))
                
                if source_candidates and target_candidates:
                    source = random.choice(source_candidates)
                    target = random.choice(target_candidates)
                    
                    if source < self.num_switches and target < self.num_switches:
                        G.add_edge(source, target)
        
        return G
    
    def _generate_tree_graph(self):
        """
        Generate a tree graph using NetworkX.

        Returns:
            nx.Graph: The generated tree graph
        """
        if self.topology_params:
            param = self._parse_params(self.topology_params)
            r = param.get('r')
            h = param.get('h')
            if r is None or h is None:
                logger.error(f"Missing parameters 'r' or 'h' for {self.topology_type}")
                sys.exit(1)
        else:
            logger.error(f"Missing parameters for {self.topology_type}")
            sys.exit(1)
        
        total_nodes = sum(r**i for i in range(h + 1))
        
        # Validate that the tree size matches the number of switches
        if total_nodes < self.num_switches:
            logger.error(
                f"Tree graph size (r={r}, h={h} = {total_nodes} nodes) is smaller than "
                f"requested number of switches ({self.num_switches}). Please adjust either "
                f"the tree parameters or the number of switches."
            )
            sys.exit(1)
        elif total_nodes > self.num_switches:
            logger.error(
                f"Tree graph size (r={r}, h={h} = {total_nodes} nodes) is larger than "
                f"requested number of switches ({self.num_switches}). Please adjust either "
                f"the tree parameters or the number of switches to match."
            )
            sys.exit(1)
        
        return nx.balanced_tree(r, h)

    def _get_next_port(self, node_id: str, connection_type: str = "default") -> int:
        """
        Get the next available port for a node using a smart port management strategy.
        
        Args:
            node_id: The ID of the node (switch)
            connection_type: The type of connection being made (e.g., "domain_connection", "switch_to_switch", "switch_to_end_system")
            
        Returns:
            int: The next available port number for the node
        
        """
        if node_id not in self.used_ports:
            self.used_ports[node_id] = set()
        
        port_priorities = {
            "domain_connection": [0, 1],
            "switch_to_switch": [2, 3, 4, 5],
            # Allow more ports for end systems to avoid warnings
            "switch_to_end_system": [6, 7, 0, 1, 2, 3, 4, 5],
            "default": list(range(8))
        }
        
        priority_ports = port_priorities.get(connection_type, port_priorities["default"])
        
        for port in priority_ports:
            if port not in self.used_ports[node_id]:
                return port
        
        # If no ports available in priority order, try any available port
        for port in range(8):
            if port not in self.used_ports[node_id]:
                logger.warning(
                    f"Switch {node_id} is using port {port} for {connection_type} connection "
                    f"outside of its priority range. This might affect network performance."
                )
                return port
        
        logger.error(
            f"Switch {node_id} has no more available ports (all 8 ports are in use).\n"
            f"Possible solutions:\n"
            f"1. Reduce the number of connections in the topology\n"
            f"2. Increase the number of switches to distribute the load\n"
            f"3. Adjust the topology parameters to create a less dense network"
        )
        sys.exit(1)
    
    def _connect_domains(self, domain_graphs: List[nx.Graph], topology: Dict) -> None:
        """
        Connect multiple domains based on the specified connection type.
        
        Args:
            domain_graphs: List of domain graphs
            topology: The topology definition to update
        """
        if self.domain_connection_type == "line":
            self._connect_domains_line(domain_graphs, topology)
        elif self.domain_connection_type == "square":
            self._connect_domains_square(domain_graphs, topology)
        elif self.domain_connection_type == "random":
            self._connect_domains_random(domain_graphs, topology)
        else:
            logger.warning(f"Unknown domain connection type: {self.domain_connection_type}. Using line connection.")
            self._connect_domains_line(domain_graphs, topology)
    
    def _connect_domains_line(self, domain_graphs: List[nx.Graph], topology: Dict) -> None:
        """
        Connect domains in a line (domain 0 to 1, 1 to 2, etc.).
        
        Args:
            domain_graphs: List of domain graphs
            topology: The topology definition to update
        """
        for i in range(len(domain_graphs) - 1):
            self._connect_domain_pair(i, i + 1, domain_graphs, topology)
    
    def _connect_domains_square(self, domain_graphs: List[nx.Graph], topology: Dict) -> None:
        """
        Connect domains in a square grid pattern where possible.
        
        Args:
            domain_graphs: List of domain graphs
            topology: The topology definition to update
        """
        # Calculate grid dimensions
        n = int(len(domain_graphs) ** 0.5)
        m = (len(domain_graphs) + n - 1) // n
        
        for i in range(len(domain_graphs)):
            row, col = i // m, i % m
            
            # Connect to right and bottom neighbor
            if col < m - 1 and i + 1 < len(domain_graphs):
                self._connect_domain_pair(i, i + 1, domain_graphs, topology)
        
            if row < n - 1 and i + m < len(domain_graphs):
                self._connect_domain_pair(i, i + m, domain_graphs, topology)
    
    def _connect_domains_random(self, domain_graphs: List[nx.Graph], topology: Dict) -> None:
        """
        Connect domains randomly, ensuring all domains are connected.
        
        Args:
            domain_graphs: List of domain graphs
            topology: The topology definition to update
        """
        # Create a random spanning tree of domains
        domain_tree = nx.random_powerlaw_tree(len(domain_graphs))
        
        for u, v in domain_tree.edges():
            self._connect_domain_pair(u, v, domain_graphs, topology)
        
        # Add additional random connections if needed
        num_extra_connections = max(0, (len(domain_graphs) * (len(domain_graphs) - 1)) // 4 - (len(domain_graphs) - 1))
        
        all_possible_connections = [(i, j) for i in range(len(domain_graphs)) for j in range(i + 1, len(domain_graphs))]
        existing_connections = list(domain_tree.edges())
        
        for i, j in random.sample([c for c in all_possible_connections if c not in existing_connections], 
                                  min(num_extra_connections, len(all_possible_connections) - len(existing_connections))):
            self._connect_domain_pair(i, j, domain_graphs, topology)
    
    def _connect_domain_pair(self, domain1: int, domain2: int, domain_graphs: List[nx.Graph], topology: Dict) -> None:
        """
        Connect two domains by adding links between them.
        
        Args:
            domain1: The ID of the first domain
            domain2: The ID of the second domain
            domain_graphs: List of domain graphs
            topology: The topology definition to update
        """
        # Select random switches from each domain for connection
        switches1 = [n for n in domain_graphs[domain1].nodes() 
                    if domain_graphs[domain1].nodes[n]["type"] == "switch"]
        switches2 = [n for n in domain_graphs[domain2].nodes() 
                    if domain_graphs[domain2].nodes[n]["type"] == "switch"]
        
        if not switches1 or not switches2:
            logger.warning(f"Cannot connect domains {domain1} and {domain2}: missing switches")
            return
        
        # Connect the specified number of switch pairs
        for _ in range(min(self.connections_per_domain_pair or 1, len(switches1), len(switches2))):
            switch1 = random.choice(switches1)
            switch2 = random.choice(switches2)
            
            # Get next available ports with domain connection priority
            port1 = self._get_next_port(switch1, "domain_connection")
            port2 = self._get_next_port(switch2, "domain_connection")
            
            # Create forward link
            link_id_forward = f"Link{self.link_counter}"
            self.link_counter += 1
            
            # Get link properties for domain connection
            link_properties = self._generate_link_properties(switch1, switch2, "domain_connection")
            
            link_data_forward = {
                "id": link_id_forward,
                "source": switch1,
                "sourcePort": port1,
                "destination": switch2,
                "destinationPort": port2,
                "domain": domain1,
                "connection_type": "domain_connection",
                **link_properties
            }
            
            # Create reverse link
            link_id_reverse = f"Link{self.link_counter}"
            self.link_counter += 1
            
            link_data_reverse = {
                "id": link_id_reverse,
                "source": switch2,
                "sourcePort": port2,
                "destination": switch1,
                "destinationPort": port1,
                "domain": domain2,
                "connection_type": "domain_connection",
                **link_properties
            }
            
            # Add the links to the topology
            topology["links"].append(link_data_forward)
            topology["links"].append(link_data_reverse)
            
            # Update used ports
            self.used_ports[switch1].add(port1)
            self.used_ports[switch2].add(port2)
            
            # Remove selected switches to avoid duplicates
            switches1.remove(switch1)
            switches2.remove(switch2)
            
            if not switches1 or not switches2:
                break

    def _get_node_domain(self, node_id: str) -> int:
        """
        Get the domain of a node from its ID.
        
        Args:
            node_id: The node ID
            
        Returns:
            int: The domain ID, or 0 if not found
        """
        # Check each domain graph for the node
        for domain_id, domain_graph in enumerate(self.domain_graphs):
            if node_id in domain_graph.nodes():
                return domain_id
        
        # Default to domain 0 if not found
        return 0