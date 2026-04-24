import json
import pytest
from tsn_case_gen_.app.tsn_case_gen import TSNTestCaseGenerator

@pytest.fixture
def test_output_dir(tmp_path):
    #Create a temporary directory for test outputs.
    return str(tmp_path)

@pytest.fixture
def basic_config(test_output_dir):
    #Basic configuration for testing.
    return {
        "delay_units": "MICRO_SECOND",
        "general": {
            "num_test_cases": 1,
            "output_directory": test_output_dir,
            "num_domains": 1,
            "topology_size": {
                "num_switches": 4,
                "num_end_systems": 8,
                "end_systems_per_switch": [0, 4]
            },
            "cross_domain_streams": 0,
            "test_case_naming": "test_case_{}"
        },
        "network": {
            "topology_type": "mesh_graph",
            "parameters": "{'n': 2, 'm': 2}",
            "default_bandwidth_mbps": 1000,
            "constraints": {
                "max_path_length": 5
            }
        },
        "routing": {
            "consider_link_utilization": True
        },
        "domain_connections": {
            "type": "line",
            "connections_per_domain_pair": 1
        },
        "traffic": {
            "types": [
                {
                    "name": "ISOCHRONOUS",
                    "PCP-list": [7],
                    "number": 10,
                    "redundant_number": 0,
                    "redundant_routes": 0,
                    "cycle_time": {
                        "cycle_time_units": "MICRO_SECOND",
                        "choose_list": True,
                        "cycle_time_list": [100, 500, 1000],
                        "min_cycle_time": 100,
                        "max_cycle_time": 1000
                    },
                    "min_delay": 100,
                    "max_delay": 1000,
                    "min_packet_size": 64,
                    "max_packet_size": 1500,
                    "bidirectional": False
                }
            ]
        }
    }

@pytest.fixture
def config_file(basic_config, tmp_path):
    #Create a temporary config file.
    config_path = tmp_path / "test_config.json"
    with open(config_path, 'w') as f:
        json.dump(basic_config, f)
    return str(config_path)

@pytest.fixture
def tsn_generator(config_file):
    #Create a TSNTestCaseGenerator instance.
    return TSNTestCaseGenerator(config_file, seed=42) 