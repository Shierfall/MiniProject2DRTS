import pytest
from tsn_case_gen_.domain.utils_functions import get_delays_from_traffic_type

# --- Fixtures ---
@pytest.fixture
def sample_traffic_types():
    """Provides a sample traffic_types list for testing."""
    return [
        {
            "name": "ISOCHRONOUS",
            "PCP-list": [7],
            "number": 2,
            "redundant_number": 1,
            "redundant_routes": 1,
            "cycle_time": {
              "cycle_time_units": "MICRO_SECOND",
              "choose_list": True,
              "cycle_time_list": [
                  100,
                500,
                1000,
                2000
              ],
              "min_cycle_time": 100,
              "max_cycle_time": 2000
            },
            "min_delay": 100,
            "max_delay": 2000,
            "min_packet_size": 30,
            "max_packet_size": 100,
            "bidirectional": False
          },
          {
            "name": "CYCLIC-SYNCHRONOUS",
            "PCP-list": [6],
            "number": 1,
            "cycle_time": {
              "cycle_time_units": "MICRO_SECOND",
              "choose_list": True,
              "cycle_time_list": [
                500, 
                1000
              ],
              "min_cycle_time": 500,
              "max_cycle_time": 1000
            },
            "min_delay": 500,
            "max_delay": 1000,
            "min_packet_size": 50,
            "max_packet_size": 1000,
            "bidirectional": False
          },
          {
            "name": "CYCLIC-ASYNCHRONOUS",
            "PCP-list": [5],
            "number": 1,
            "cycle_time": {
              "cycle_time_units": "MICRO_SECOND",
              "choose_list": True,
              "cycle_time_list": [
                2000,
                10000,
                                20000
              ],
              "min_cycle_time": 2000,
              "max_cycle_time": 20000
            },
            "min_delay": 2000,
            "max_delay": 20000,
            "min_packet_size": 50,
            "max_packet_size": 1000,
            "bidirectional": False
          },
          {
            "name": "NETWORK-CONTROL",
            "PCP-list": [4],
            "number": 1,
            "cycle_time": {
              "cycle_time_units": "MICRO_SECOND",
              "choose_list": True,
              "cycle_time_list": [
                50000,
                100000,
                500000,
                1000000
              ],
              "min_cycle_time": 50000,
              "max_cycle_time": 1000000
            },
            "min_delay": 50000,
            "max_delay": 1000000,
            "min_packet_size": 50,
            "max_packet_size": 500,
            "bidirectional": False
          },
          {
            "name": "ALARMS-AND-EVENTS",
            "PCP-list": [3],
            "number": 1,
            "cycle_time": {
              "cycle_time_units": "MICRO_SECOND",
              "choose_list": True,
              "cycle_time_list": [
                100000,
                500000,
                1000000
              ],
              "min_cycle_time": 100000,
              "max_cycle_time": 1000000
            },
            "min_delay": 100000,
            "max_delay": 1000000,
            "min_packet_size": 50,
            "max_packet_size": 1500,
            "bidirectional": False
          },
          {
            "name": "CONFIGURATION-AND-DIAGNOSTICS",
            "PCP-list": [2],
            "number": 1,
            "cycle_time": {
              "cycle_time_units": "MICRO_SECOND",
              "choose_list": True,
              "cycle_time_list": [
                500000,
                1000000,
                1500000,
                2000000
              ],
              "min_cycle_time": 500000,
              "max_cycle_time": 2000000
            },
            "min_delay": 500000,
            "max_delay": 2000000,
            "min_packet_size": 500,
            "max_packet_size": 1500,
            "bidirectional": False
          },
          {
            "name": "VIDEO",
            "PCP-list": [1],
            "number": 1,
            "cycle_time": {
              "cycle_time_units": "MICRO_SECOND",
              "choose_list": True,
              "cycle_time_list": [
                                16700,
                                33300
                            ],
              "min_cycle_time": 2000,
              "max_cycle_time": 10000
            },
            "min_delay": 2000,
            "max_delay": 10000,
            "min_packet_size": 1000,
            "max_packet_size": 1500,
            "bidirectional": False
          },
          {
            "name": "BEST-EFFORT",
            "PCP-list": [0],
            "number": 1,
            "min_packet_size": 30,
            "max_packet_size": 1500,
            "bidirectional": False
          },
          {
            "name": "AUDIO/VOICE",
            "PCP-list": [0],
            "number": 1,
            "min_delay": 1,
            "max_delay": 100000,
            "min_packet_size": 1000,
            "max_packet_size": 1500,
            "bidirectional": False
          }
    ]

# --- Tests of get_delays_from_traffic_type ---

def test_get_delays_found(sample_traffic_types):
    min_delay, max_delay = get_delays_from_traffic_type("ISOCHRONOUS", sample_traffic_types)
    assert min_delay == 100
    assert max_delay == 2000

def test_get_delays_not_found(sample_traffic_types):
    result = get_delays_from_traffic_type("AUDIO", sample_traffic_types)
    assert result is None

def test_get_delays_missing_keys(sample_traffic_types):
    result = get_delays_from_traffic_type("BEST-EFFORT", sample_traffic_types)
    assert result == (None, None)

def test_get_delays_empty_list():
    result = get_delays_from_traffic_type("ISOCHRONOUS", [])
    assert result is None