"""
utils_functions.py

Domain utility module for TSN test case generation.

Provides helper functions for extracting delay values and other domain-specific utilities used by generators and validators.

Features:
    - get_delays_from_traffic_type: Extracts min/max delay for a given traffic type from config.

Usage:
    min_delay, max_delay = get_delays_from_traffic_type("ISOCHRONOUS", traffic_types)

Main Functions:
    - get_delays_from_traffic_type: Returns (min_delay, max_delay) tuple for a traffic type name.
"""
from typing import Tuple
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def get_delays_from_traffic_type(traffic_type_name: str, traffic_types: List[Dict]) -> Optional[Tuple[int, int]]:
    """
    Get the min and max delay for a given traffic type name from the list of traffic types.

    Args:
        traffic_type_name (str): _description_
        traffic_types (List[Dict]): _description_

    Returns:
        Optional[Tuple[int, int]]: _description_
    """
    for traffic_type in traffic_types:
        if traffic_type.get("name") == traffic_type_name:
            min_delay = traffic_type.get("min_delay")
            max_delay = traffic_type.get("max_delay")
            return min_delay, max_delay