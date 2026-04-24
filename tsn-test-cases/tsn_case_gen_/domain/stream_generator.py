"""
stream_generator.py

Domain service for generating network streams for TSN test cases.

This module provides the StreamGenerator class, which creates streams based on topology and traffic type definitions.
It supports intra-domain and cross-domain stream generation, realistic period/packet size/deadline modeling, and harmonicity enforcement.

Features:
    - Generates streams for each traffic type, supporting redundancy and bidirectionality.
    - Supports cross-domain stream generation for multi-domain topologies.
    - Realistic modeling of periods, packet sizes, and deadlines using statistical distributions.
    - Enforces harmonicity of stream periods for scheduling feasibility.
    - Selects sources/destinations to balance usage across end systems.

Usage:
    generator = StreamGenerator(topology, traffic_types, ...)
    streams = generator.generate()

Main Class:
    - StreamGenerator: Encapsulates all stream generation logic and domain knowledge.

Raises:
    - SystemExit: For missing required config fields or invalid traffic types.
    - Warnings: For insufficient end systems or unknown traffic types.
"""
from itertools import combinations
import logging
import random
import sys
from typing import Dict, List
import numpy as np
from math import gcd, lcm
from functools import reduce


logger = logging.getLogger(__name__)

class StreamGenerator:
    """Generate network streams for TSN test cases."""
    
    def __init__(
        self,
        topology: Dict,
        traffic_types: List[Dict],
        delay_units: str = "MICRO_SECOND",
        num_domains: int = 1,
        cross_domain_streams: int = 0
    ):
        """
        Initialize the stream generator.
        
        Args:
            topology: The generated topology
            traffic_types: List of traffic type definitions from the configuration
            delay_units: Units for delay values
            num_domains: Number of TSN domains
            cross_domain_streams: Number of cross-domain streams to generate (only for multi-domain)
        """
        self.topology = topology
        self.traffic_types = traffic_types
        self.delay_units = delay_units
        self.num_domains = num_domains
        self.cross_domain_streams = cross_domain_streams
        
        # Extract nodes from the topology
        self.end_systems_by_domain = self._get_end_systems_by_domain()
        
        # Counter for stream IDs
        self.stream_counter = 0
        
    def generate(self) -> Dict:
        """
        Generate all streams based on the traffic type definitions.
        
        Returns:
            Dict: The complete streams definition
        """
        # Initialize streams structure
        streams_def = {
            "delay_units": self.delay_units,
            "streams": []
        }
        
        # Generate intra-domain streams for each traffic type
        for traffic_type in self.traffic_types:
            streams = self._generate_streams_for_type(traffic_type)
            
            streams_def["streams"].extend(streams)
        
        # Generate cross-domain streams if needed
        if self.num_domains > 1 and self.cross_domain_streams > 0:
            cross_domain_streams = self._generate_cross_domain_streams()
            streams_def["streams"].extend(cross_domain_streams)
            
        logger.info(f"Generated {len(streams_def['streams'])} streams")
        
        # Enforce strict harmonicity across all generated streams (final global check)
        all_periods = [s["period"] for s in streams_def["streams"] if s.get("period") is not None]
        if all_periods:
            harmonic_periods = self._ensure_harmonicity(all_periods, suppress_warning=False)
            if set(harmonic_periods) != set(all_periods):
                logger.warning("The final set of generated stream periods is not strictly harmonic. Adjusting to closest harmonic set.")
                # Adjust periods to the closest harmonic set actually used
                period_map = {p: harmonic_periods[min(range(len(harmonic_periods)), key=lambda i: abs(harmonic_periods[i] - p))] for p in all_periods}
                for s in streams_def["streams"]:
                    if s.get("period") is not None:
                        s["period"] = period_map[s["period"]]

        return streams_def
    
    def _validate_harmonic_periods(self, periods, suppress_warning=True):
        """
        Validate if the given periods are harmonic.

        Args:
            periods: List of period values to validate
            suppress_warning: If True, suppress warnings for large hyperperiods

        Returns:
            bool: True if the periods are harmonic, False otherwise
        """
        if not periods:
            return True
        hyperperiod = reduce(lcm, periods)
        if hyperperiod > 1_000_000:
            if not suppress_warning:
                logger.warning(f"Very large hyperperiod detected: {hyperperiod} µs")
            return False
        return True
        
    def _get_end_systems_by_domain(self) -> Dict[int, List[str]]:
        """
        Group end systems by domain.
        
        Returns:
            Dict[int, List[str]]: Dictionary mapping domain IDs to lists of end system IDs
        """
        end_systems = {}
        
        # Use the new end_systems array with domain field
        for node in self.topology.get("end_systems", []):
            domain = node.get("domain", 0)
            
            if domain not in end_systems:
                end_systems[domain] = []
            
            end_systems[domain].append(node["id"])
        
        return end_systems
    
    def _ensure_harmonicity(self, period_values, suppress_warning=True):
        """
        Ensure that the given period values are harmonic.

        Args:
            period_values: List of period values to ensure harmonicity
            suppress_warning: If True, suppress warnings for large hyperperiods

        Returns:
            List[int]: List of harmonic period values
        """
        if not period_values:
            return []
        sorted_periods = sorted(period_values)
        base_period = reduce(gcd, sorted_periods)
        if base_period == 1:
            min_period = sorted_periods[0]
            harmonic_periods = []
            factor = 1
            while len(harmonic_periods) < 4:
                harmonic_periods.append(factor * min_period)
                factor *= 2
            is_harmonic = self._validate_harmonic_periods(harmonic_periods, suppress_warning=suppress_warning)
            if not is_harmonic and not suppress_warning:
                logger.warning("Some streams may have excessive hyperperiods.")
            return harmonic_periods
        harmonic_periods = [p for p in sorted_periods if p % base_period == 0]
        is_harmonic = self._validate_harmonic_periods(harmonic_periods, suppress_warning=suppress_warning)
        if not is_harmonic and not suppress_warning:
            logger.warning("Some streams may have excessive hyperperiods.")
        return harmonic_periods
            
    def _generate_realistic_packet_size(self, traffic_type, min_size, max_size):
        """
        Generate realistic packet sizes based on traffic type. Uses different distributions.
        The function uses a normal distribution for most types, but can also use uniform or Poisson distributions.
        
        Args:
            traffic_type: The type of traffic (e.g., "ISOCHRONOUS", "VIDEO")
            min_size: Minimum packet size
            max_size: Maximum packet size
            
        Returns:
            int: A realistic packet size
        """
        if traffic_type == "ISOCHRONOUS":
            mean = np.mean([min_size, max_size])
            std_dev = (max_size - min_size) / 6
            size = int(np.random.normal(mean, std_dev))
            return max(min_size, min(max_size, size))
        
        elif traffic_type == "CYCLIC-SYNCHRONOUS" or traffic_type == "CYCLIC-ASYNCHRONOUS":
            lambda_value = min_size + (max_size - min_size) * 0.2

            packet_size = np.random.poisson(lambda_value)

            return max(min_size, min(packet_size, max_size))
        
        elif traffic_type == "AUDIO/VOICE":
            size = int(np.random.uniform(min_size, max_size + 1))
            return max(min_size, min(size, max_size))
        
        elif traffic_type == "VIDEO":
            if random.random() < 0.9:
                return random.randint(max(min_size, 1400), max_size)
            else:
                return random.randint(min(max_size, 800), min_size)
            
        elif traffic_type == "CONFIGURATION-AND-DIAGNOSTICS":
            return random.randint(max(min_size, max_size - 300), max_size)

        elif traffic_type == "ALARMS-AND-EVENTS":
            mean = min_size + (max_size - min_size) / 3
            std_dev = (max_size - min_size) / 4
            size = int(np.random.normal(mean, std_dev))
            return max(min_size, min(max_size, size))
        
        elif traffic_type == "NETWORK-CONTROL":
            return random.randint(min_size, min(max_size, 100))
        
        elif traffic_type == "BEST-EFFORT":

            r = random.random()
            if r < 0.7:
                return min_size
            elif r < 0.85:
                return min(max_size, max(min_size, 570))
            else:
                return max_size
            
        elif traffic_type == "CYCLIC-SCHEDULED":
            mean = np.mean([min_size, max_size])
            std_dev = np.std([min_size, max_size])
            size = int(np.random.normal(mean, std_dev))
            return max(min_size, min(max_size, size))
        
        elif traffic_type == "HIGH-RESOLUTION-SENSOR":
            mean = max_size - (max_size - min_size) * 0.1
            std_dev = (max_size - min_size) / 10
            size = int(np.random.normal(mean, std_dev))
            return max(min_size, min(max_size, size))
        
        elif traffic_type == "ACOUSTIC-SENSOR":
            mean = np.mean([min_size, max_size])
            std_dev = (max_size - min_size) / 10
            size = int(np.random.normal(mean, std_dev))
            return max(min_size, min(max_size, size))
        
        elif traffic_type == "FLEXRAY":
            mean = np.mean([min_size, max_size])
            std_dev = (max_size - min_size) / 8
            size = int(np.random.normal(mean, std_dev))
            return max(min_size, min(max_size, size))
        
        elif traffic_type == "COMMAND-AND-CONTROL":
            mean = np.mean([min_size, max_size])
            std_dev = (max_size - min_size) / 6
            size = int(np.random.normal(mean, std_dev))
            return max(min_size, min(max_size, size))
        
        elif traffic_type == "SYNC-PARAMETRIC":
            mean = np.mean([min_size, max_size])
            std_dev = (max_size - min_size) / 8
            size = int(np.random.normal(mean, std_dev))
            return max(min_size, min(max_size, size))
        
        elif traffic_type == "ASYNC-PARAMETRIC":
            lambda_value = min_size + (max_size - min_size) * 0.3
            packet_size = np.random.poisson(lambda_value)
            return max(min_size, min(packet_size, max_size))
        
        elif traffic_type == "MAINTENANCE":
            return random.randint(min_size, max_size)
        
        elif traffic_type == "FILE-TRANSFER":
            if random.random() < 0.8:
                return random.randint(int(max_size * 0.8), max_size)
            else:
                return random.randint(min_size, int(max_size * 0.8))
            
        elif traffic_type == "AUDIO":
            size = int(np.random.uniform(min_size, max_size + 1))
            return max(min_size, min(size, max_size))
            
        else:
            logger.warning("No compatible traffic type to generate realistic packet sizes, using random selection.")
            return random.randint(min_size, max_size)
    
    def _generate_realistic_deadline(self, name, min_delay, max_delay, period=None):
        """
        Generate realistic deadlines based on traffic type. Uses different distributions.
        The function uses a normal distribution for most types, but can also use uniform or exponential distributions.

        Args:
            name: traffic_type
            min_delay: minimum delay
            max_delay: maximum delay
            period: period of stream. Defaults to None.

        Returns:
            int: deadline of the given traffic type
        """
        if period is not None:
            if name in ["CYCLIC-SYNCHRONOUS", "CYCLIC-ASYNCHRONOUS"]:
                deadline = int(period * random.uniform(0.5, 0.9))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "VIDEO":
                mean_deadline = period
                std_dev = period * 0.1
                deadline = int(random.gauss(mean_deadline, std_dev))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "AUDIO/VOICE":
                mean_deadline = period
                std_dev = period * 0.05
                deadline = int(random.gauss(mean_deadline, std_dev))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "NETWORK-CONTROL":
                mean_deadline = period
                deadline = int(random.uniform(min_delay, max_delay))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "ALARMS-AND-EVENTS":
                scale = (max_delay - min_delay) / 2
                deadline = int(random.expovariate(1 / scale))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "CONFIGURATION-AND-DIAGNOSTICS":
                mean_deadline = period
                std_dev = period * 0.05
                deadline = int(random.gauss(mean_deadline, std_dev))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "ISOCHRONOUS":
                deadline = int(random.uniform(min_delay, max_delay))
                deadline = max(min_delay, min(max_delay, deadline))
                
            elif name == "COMMAND-AND-CONTROL":
                deadline = int(period * random.uniform(0.3, 0.6))
                deadline = max(min_delay, min(max_delay, deadline))
                
            elif name == "SYNC-PARAMETRIC":
                deadline = int(period * random.uniform(0.5, 0.9))
                deadline = max(min_delay, min(max_delay, deadline))
                
            elif name == "ASYNC-PARAMETRIC":
                scale = (max_delay - min_delay) / 3
                deadline = int(random.expovariate(1 / scale))
                deadline = max(min_delay, min(max_delay, deadline))
                
            elif name == "AUDIO":
                mean_deadline = period
                std_dev = period * 0.03
                deadline = int(random.gauss(mean_deadline, std_dev))
                deadline = max(min_delay, min(max_delay, deadline))
                
            elif name == "MAINTENANCE":
                deadline = random.randint(min_delay, max_delay)
                
            elif name == "FILE-TRANSFER":
                if period is not None:
                    deadline = min(period, random.randint(min_delay, max_delay))
                else:
                    deadline = random.randint(min_delay, max_delay)
            
            elif name == "CYCLIC-SCHEDULED":
                deadline = int(period * random.uniform(0.5, 0.9))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "HIGH-RESOLUTION-SENSOR":
                mean_deadline = period
                std_dev = period * 0.05
                deadline = int(random.gauss(mean_deadline, std_dev))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "ACOUSTIC-SENSOR":
                mean_deadline = period
                std_dev = period * 0.02
                deadline = int(random.gauss(mean_deadline, std_dev))
                deadline = max(min_delay, min(max_delay, deadline))
            
            elif name == "FLEXRAY":
                deadline = int(period * random.uniform(0.8, 0.95))
                deadline = max(min_delay, min(max_delay, deadline))
            
            else:
                deadline = random.randint(min_delay, max_delay)
        
        else:
            deadline = random.randint(min_delay, max_delay)
    
        if period is not None:
            deadline = min(deadline, period)
        return deadline
        
    def _generate_streams_for_type(self, traffic_type: Dict) -> List[Dict]:
        """
        Generate streams for a specific traffic type.
        
        Args:
            traffic_type: The traffic type definition
            
        Returns:
            List[Dict]: List of generated stream definitions
        """
        streams = []
        
        # Extract parameters from the traffic type
        name = traffic_type["name"]
        num_streams = traffic_type["number"]
        redundant_number = traffic_type.get("redundant_number", 0)
        redundant_routes = traffic_type.get("redundant_routes", 0)
        pcp_list = traffic_type.get("PCP-list", [0])
        bidirectional = traffic_type.get("bidirectional", False)
        
        logger.debug(f"Generating {num_streams} streams for traffic type {name}")
        
        # Determine period based on cycle_time or old style fields
        if "cycle_time" in traffic_type:
            cycle_time = traffic_type["cycle_time"]
            period_values = self._get_period_values_from_cycle_time(cycle_time)
        elif "cycle_time" not in traffic_type and (name == "BEST-EFFORT" or name == "AUDIO/VOICE"):
            period_values = None
            cycle_time = None
        else:
            logger.error("Cycle time not set, please set cycle time")
            sys.exit(1)
        
        # Get packet size range
        min_packet_size = traffic_type.get("min_packet_size", 64)
        max_packet_size = traffic_type.get("max_packet_size", 1500)
        
        # Get deadline range
        min_delay = traffic_type.get("min_delay", None)
        max_delay = traffic_type.get("max_delay", None)
        
        # Allow BEST-EFFORT to proceed without delay values
        if min_delay is None or max_delay is None:
            if name != "BEST-EFFORT":
                logger.error("Please define min_delay and max_delay in the configuration file.")
                sys.exit(1)
    
        used_sources = {}
        used_destinations = {}
        
        # Generate the specified number of streams
        for i in range(num_streams):
            has_redundancy = i < redundant_number
            
            domain = random.randrange(self.num_domains)
            
            if domain not in self.end_systems_by_domain or len(self.end_systems_by_domain[domain]) < 2:
                logger.warning(f"Not enough end systems in domain {domain} to create streams. Skipping.")
                continue
            
            # Choose source that has been used the least
            domain_end_systems = self.end_systems_by_domain[domain]
            source = self._select_least_used_node(domain_end_systems, used_sources)
            used_sources[source] = used_sources.get(source, 0) + 1
            
            pcp = random.choice(pcp_list)
            
            # Generate realistic period
            if not period_values:
                if name not in ["BEST-EFFORT", "AUDIO/VOICE"]:
                    logger.error(f"Missing period values for traffic type: {name}")
                    sys.exit(1)
                else:
                    period = None
            else:
                period = self._generate_realistic_period(name, period_values)

            size = self._generate_realistic_packet_size(name, min_packet_size, max_packet_size)
            
            # Choose destination(s) that have been used the least
            potential_destinations = [es for es in domain_end_systems if es != source]
            
            # Determine number of destinations (1-3 for most types, 1-5 for multicast types)
            multicast_types = ["VIDEO", "ALARMS-AND-EVENTS", "CONFIGURATION-AND-DIAGNOSTICS"]
            max_destinations = 5 if name in multicast_types else 3
            num_destinations = random.randint(1, min(max_destinations, len(potential_destinations)))
            
            # Select destinations
            destinations = []
            for _ in range(num_destinations):
                if not potential_destinations:
                    break
                destination = self._select_least_used_node(potential_destinations, used_destinations)
                used_destinations[destination] = used_destinations.get(destination, 0) + 1
                potential_destinations.remove(destination)
                
                # Generate individual deadline for each destination
                if min_delay is None or max_delay is None:
                    if name != "BEST-EFFORT":
                        logger.error(f"Missing min and max delay for traffic type: {name}")
                        sys.exit(1)
                    else:
                        dest_deadline = None
                else:
                    dest_deadline = self._generate_realistic_deadline(name, min_delay, max_delay, period)
                
                destinations.append({"id": destination, "deadline": dest_deadline})
                    
            # Create the stream
            stream = {
                "id": self.stream_counter,
                "name": f"Stream{self.stream_counter}",
                "source": source,
                "destinations": destinations,
                "type": name,
                "PCP": pcp,
                "size": size,
                "period": period,
                "redundancy": redundant_routes if has_redundancy else 0
            }
            
            streams.append(stream)
            self.stream_counter += 1
            
            # Create reverse stream if bidirectional
            if bidirectional:
                # For bidirectional streams, create a single reverse stream using the first destination
                if destinations:  # Only create reverse stream if there are destinations
                    reverse_stream = {
                        "id": self.stream_counter,
                        "name": f"Stream{self.stream_counter}",
                        "source": destinations[0]["id"],  # Use first destination as source
                        "destinations": [{"id": source, "deadline": destinations[0]["deadline"]}],
                        "type": name,
                        "PCP": pcp,
                        "size": size,
                        "period": period,
                        "redundancy": redundant_routes if has_redundancy else 0
                    }
                    
                    streams.append(reverse_stream)
                    self.stream_counter += 1
            
        return streams
    
    def _generate_realistic_period(self, traffic_type, period_values):
        """
        Generate realistic periods based on traffic type. Uses different distributions.
        The function uses a normal distribution for most types, but can also use uniform or exponential distributions.

        Args:
            traffic_type: traffic type of the given stream
            period_values: list of period values

        Returns:
            List[int]: list of valid period values
        """
        if not period_values:
            return None
        
        period_values = sorted(period_values)
        
        if traffic_type == "ISOCHRONOUS":
            short_periods = [p for p in period_values if p <= 2000]
            if short_periods:
                return random.choice(short_periods)
        
        elif traffic_type == "CYCLIC-SYNCHRONOUS" or traffic_type == "CYCLIC-ASYNCHRONOUS":
            weights = []
            for p in period_values:
                if p in [2000, 4000, 8000, 16000]:
                    weights.append(3.0)
                elif 2000 <= p <= 20000:
                    weights.append(2.0)
                else:
                    weights.append(1.0)
            
            # Normalize weights
            total = sum(weights)
            weights = [w/total for w in weights]
            
            return random.choices(period_values, weights=weights, k=1)[0]
        
        elif traffic_type == "VIDEO":
            for target in [16700, 33300]:
                closest = min(period_values, key=lambda x: abs(x - target))
                if abs(closest - target) < 5000:
                    return closest
            # Fallback: return the first available period
            return period_values[0]
        
        elif traffic_type == "NETWORK-CONTROL":
            long_periods = [p for p in period_values if p >= 50000]
            if long_periods:
                return random.choice(long_periods)
    
        elif traffic_type == "ALARMS-AND-EVENTS":
            return random.choice(period_values)
    
        elif traffic_type == "CONFIGURATION-AND-DIAGNOSTICS":
            long_periods = [p for p in period_values if p >= 500000]
            if long_periods:
                return random.choice(long_periods)
        
        elif traffic_type == "CYCLIC-SCHEDULED":
            short_periods = [p for p in period_values if p <= 5000]
            if short_periods:
                weights = [1.0 / p for p in short_periods]
                total = sum(weights)
                weights = [w / total for w in weights]
                return random.choices(short_periods, weights=weights, k=1)[0]
            else:
                return random.choice(period_values)
            
        elif traffic_type == "HIGH-RESOLUTION-SENSOR":
            valid = [p for p in period_values if p <= 200]
            if valid:
                weights = [1.0 / p for p in valid]
                total = sum(weights)
                weights = [w / total for w in weights]
                return random.choices(valid, weights=weights, k=1)[0]
            else:
                return random.choice(period_values)
        
        elif traffic_type == "ACOUSTIC-SENSOR":
            valid = [p for p in period_values if p <= 50]
            if valid:
                target = 22.5
                closest = min(valid, key=lambda x: abs(x - target))
                return closest
            else:
                return random.choice(period_values)
            
        elif traffic_type == "FLEXRAY":
            valid = [p for p in period_values if 40 <= p <= 150]
            if valid:
                target = 50
                closest = min(valid, key=lambda x: abs(x - target))
                return closest
            else:
                return random.choice(period_values)
        
        elif traffic_type == "COMMAND-AND-CONTROL":
            fast_periods = [p for p in period_values if p <= 2000]
            if fast_periods:
                return random.choice(fast_periods)
            
        elif traffic_type == "SYNC-PARAMETRIC":
            weights = []
            for p in period_values:
                if p in [1000, 2000, 5000]:
                    weights.append(3.0)
                elif 1000 <= p <= 10000:
                    weights.append(2.0)
                else:
                    weights.append(1.0)
            total = sum(weights)
            weights = [w/total for w in weights]
            return random.choices(period_values, weights=weights, k=1)[0]
        
        elif traffic_type == "ASYNC-PARAMETRIC":
            return random.choice(period_values)
        
        elif traffic_type == "MAINTENANCE":
            long_periods = [p for p in period_values if p >= 500000]
            return random.choice(long_periods) if long_periods else random.choice(period_values)
        
        elif traffic_type == "FILE-TRANSFER":
            high_throughput_periods = [p for p in period_values if p >= 1000000]
            return random.choice(high_throughput_periods) if high_throughput_periods else random.choice(period_values)
        
        elif traffic_type == "AUDIO":
            audio_periods = [p for p in period_values if p <= 3000]
            return random.choice(audio_periods) if audio_periods else random.choice(period_values)
        
        else:
            logger.warning("Unknown traffic type, selecting random period from cycle time list.")
            return random.choice(period_values)
    
    def _get_period_values_from_cycle_time(self, cycle_time: Dict) -> List[int]:
        """
        Extract period values from the cycle_time configuration.
        
        Args:
            cycle_time: The cycle_time configuration
            
        Returns:
            List[int]: List of valid period values
        """
        
        # If no cycle time parameters are provided, return None.
        if not cycle_time:
            return None
    
    
        # Check if we should use a list of discrete values
        if cycle_time.get("choose_list", False) and "cycle_time_list" in cycle_time:
            values = cycle_time["cycle_time_list"]
            
            harmonic_values = self._ensure_harmonicity(values)
            
            if len(harmonic_values) < len(values):
                logger.warning("Not all values in cycle_time_list are harmonic. Please evaluate cycle time list in configuration for harmonic periods")
                
            return harmonic_values
        
        # Otherwise, use the min/max range
        min_cycle_time = cycle_time.get("min_cycle_time", 1000)
        max_cycle_time = cycle_time.get("max_cycle_time", 10000)
        
        # Create an array of values (use powers of 2 as typical values)
        values = []
        value = min_cycle_time
        while value <= max_cycle_time:
            values.append(value)
            value *= 2
        
        # If no values were added, add the min and max
        if not values:
            values = [min_cycle_time, max_cycle_time]
        return values
    
    def _select_least_used_node(self, candidates: List[str], usage_counts: Dict[str, int]) -> str:
        """
        Select a node from the candidates that has been used the least.
        
        Args:
            candidates: List of candidate node IDs
            usage_counts: Dictionary mapping node IDs to usage counts
            
        Returns:
            str: The selected node ID
        """
        min_usage = min([usage_counts.get(node, 0) for node in candidates])
        
        min_usage_candidates = [node for node in candidates if usage_counts.get(node, 0) == min_usage]
        
        return random.choice(min_usage_candidates)
    
    def _generate_cross_domain_streams(self) -> List[Dict]:
        """
        Generate streams that span multiple domains.
        
        Returns:
            List[Dict]: List of cross-domain stream definitions
        """
        streams = []
        
        if self.num_domains <= 1:
            return streams
        
        high_prioritized_types = ["CONFIGURATION-AND-DIAGNOSTICS", "VIDEO", "ALARMS-AND-EVENTS", "BEST-EFFORT"]
        low_prioritized_types = ["ISOCHRONOUS", "CYCLIC-SYNCHRONOUS", "CYCLIC-ASYNCHRONOUS", "NETWORK-CONTROL", "AUDIO/VOICE"]

        # Filter available traffic types based on priority
        high_priority_valid_types = [t for t in self.traffic_types if t["name"] in high_prioritized_types]

        if high_priority_valid_types:
            template_type = random.choice(high_priority_valid_types)
        else:
            low_priority_valid_types = [t for t in self.traffic_types if t["name"] in low_prioritized_types]
            
            if low_priority_valid_types:
                template_type = random.choice(low_priority_valid_types)
            else:
                logger.error("No suitable traffic types found for cross-domain streams. Neither high nor low priority types available.")
                sys.exit(1)

        # Extract parameters
        name = template_type["name"]
        pcp_list = template_type.get("PCP-list", [0])
        
        if "cycle_time" in template_type:
            cycle_time = template_type["cycle_time"]
            period_values = self._get_period_values_from_cycle_time(cycle_time)
        else:
            if name == "BEST-EFFORT":
                period_values = None
            else:
                period_values = template_type.get("period_us", [1000])
                if not isinstance(period_values, list):
                    period_values = [period_values]
        
        # Get packet size range
        min_packet_size = template_type.get("min_packet_size", 64)
        max_packet_size = template_type.get("max_packet_size", 1500)
        
        # Get deadline range
        min_delay = template_type.get("min_delay", None)
        max_delay = template_type.get("max_delay", None)
        if (min_delay is None or max_delay is None) and name not in ["BEST-EFFORT"]:
            logger.error(f"Missing min_delay and max_delay for traffic type: {name}")
            sys.exit(1)
        
        # Get all unique domain pairs (i < j)
        domain_pairs = list(combinations(range(self.num_domains), 2))

        for source_domain, dest_domain in domain_pairs:
            for _ in range(self.cross_domain_streams):
                # Skip if either domain lacks end systems
                if (source_domain not in self.end_systems_by_domain or 
                    dest_domain not in self.end_systems_by_domain or
                    not self.end_systems_by_domain[source_domain] or
                    not self.end_systems_by_domain[dest_domain]):
                    logger.warning(f"Skipping cross-domain stream - missing end systems for domains {source_domain} and {dest_domain}")
                    continue

                source = random.choice(self.end_systems_by_domain[source_domain])
                destination = random.choice(self.end_systems_by_domain[dest_domain])
            
                pcp = random.choice(pcp_list)
                
                if not period_values:
                    if name == "BEST-EFFORT":
                        period = None
                    else:
                        logger.error(f"Missing period values for traffic type: {name}")
                        sys.exit(1)
                else:
                    period = self._generate_realistic_period(name, period_values)
                
                size = self._generate_realistic_packet_size(name, min_packet_size, max_packet_size)
                
                if min_delay is None or max_delay is None:
                    if name != "BEST-EFFORT":
                        logger.error(f"Missing min and max delay for traffic type: {name}")
                        sys.exit(1)
                    else:
                        deadline = None
                else:
                    # Make deadline more realistic - related to period
                    if period is not None:
                        if name in ["CYCLIC-SYNCHRONOUS", "CYCLIC-ASYNCHRONOUS"]:
                            deadline = int(period * random.uniform(0.5, 0.9))
                            deadline = max(min_delay, min(max_delay, deadline))
                        
                        elif name == "VIDEO":
                            mean_deadline = period
                            std_dev = period * 0.1
                            deadline = int(random.gauss(mean_deadline, std_dev))
                            deadline = max(min_delay, min(max_delay, deadline))
                        
                        elif name == "AUDIO/VOICE":
                            mean_deadline = period
                            std_dev = period * 0.05
                            deadline = int(random.gauss(mean_deadline, std_dev))
                            deadline = max(min_delay, min(max_delay, deadline))
                        
                        elif name == "NETWORK-CONTROL":
                            mean_deadline = period
                            deadline = int(random.uniform(min_delay, max_delay))
                            deadline = max(min_delay, min(max_delay, deadline))
                        
                        elif name == "ALARMS-AND-EVENTS":
                            scale = (max_delay - min_delay) / 2
                            deadline = int(random.expovariate(1 / scale))
                            deadline = max(min_delay, min(max_delay, deadline))
                        
                        elif name == "CONFIGURATION-AND-DIAGNOSTICS":
                            mean_deadline = period
                            std_dev = period * 0.05
                            deadline = int(random.gauss(mean_deadline, std_dev))
                            deadline = max(min_delay, min(max_delay, deadline))
                        
                        elif name == "ISOCHRONOUS":
                            deadline = int(random.uniform(min_delay, max_delay))
                            deadline = max(min_delay, min(max_delay, deadline))
                        
                        else:
                            logger.warning("Unknown traffic type, selecting random deadline from min- and maxdelay.")
                            deadline = random.randint(min_delay, max_delay)
                    
                    else:
                        logger.warning("No period, selecting random deadline from min- and maxdelay.")
                        deadline = random.randint(min_delay, max_delay)

                # Create the stream
                if name == "BEST-EFFORT":
                    stream = {
                        "source": source,
                        "destinations": [{"id": destination, "deadline": None}],
                        "type": name,
                        "pcp": pcp,
                        "period": None,  # Explicitly set to None
                        "packet_size": self._generate_realistic_packet_size(name, min_packet_size, max_packet_size),
                        "redundancy": 0,
                        "bidirectional": template_type.get("bidirectional", False)
                    }
                else:
                    stream = {
                        "id": self.stream_counter,
                        "name": f"Stream{self.stream_counter}",
                        "source": source,
                        "destinations": [{"id": destination, "deadline": deadline}],
                        "type": name,
                        "PCP": pcp,
                        "size": size,
                        "period": period,
                        "redundancy": 0
                    }
                    
                streams.append(stream)
                self.stream_counter += 1
        
        return streams 