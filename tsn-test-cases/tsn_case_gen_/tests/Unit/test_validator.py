import pytest
import copy
from tsn_case_gen_.domain.test_case_validation import (
    validate_topology, validate_streams, validate_routes, validate_gen_config, validate_all
)

# --- Fixtures for Valid Data ---

@pytest.fixture
def valid_topology():
    return {
         "topology": {
            "delay_units": "us", "default_bandwidth_mbps": 1000,
            "switches": [
                {"id": "SW0", "ports": 4, "domain": 0},
                {"id": "SW1", "ports": 4, "domain": 0}
            ],
            "end_systems": [
                {"id": "ES0", "domain": 0},
                {"id": "ES1", "domain": 0}
            ],
            "links": [
                {"id": "L0", "source": "ES0", "destination": "SW0", "sourcePort": 0, "destinationPort": 0, "domain": 0},
                {"id": "L1", "source": "SW0", "destination": "ES0", "sourcePort": 0, "destinationPort": 0, "domain": 0},
                {"id": "L2", "source": "SW0", "destination": "SW1", "sourcePort": 1, "destinationPort": 0, "domain": 0},
                {"id": "L3", "source": "SW1", "destination": "SW0", "sourcePort": 0, "destinationPort": 1, "domain": 0},
                {"id": "L4", "source": "SW1", "destination": "ES1", "sourcePort": 1, "destinationPort": 0, "domain": 0},
                {"id": "L5", "source": "ES1", "destination": "SW1", "sourcePort": 0, "destinationPort": 1, "domain": 0}
            ]
         }
    }

@pytest.fixture
def valid_streams():
    return {
        "delay_units": "us",
        "streams": [
            {
                "id": 0,
                "name": "S0",
                "source": "ES0",
                "destinations": [{"id": "ES1", "deadline": 500}],
                "type": "ISOCHRONOUS",
                "PCP": 7,
                "size": 100,
                "period": 1000,
                "redundancy": 0
            },
            {
                "id": 1,
                "name": "S1",
                "source": "ES0",
                "destinations": [{"id": "ES1", "deadline": None}],
                "type": "BEST-EFFORT",
                "PCP": 0,
                "size": 100,
                "period": None,
                "redundancy": 0
            },
            {
                "id": 2,
                "name": "S2",
                "source": "ES0",
                "destinations": [{"id": "ES1", "deadline": 5000}],
                "type": "AUDIO/VOICE",
                "PCP": 0,
                "size": 100,
                "period": None,
                "redundancy": 0
            }
        ]
    }

@pytest.fixture
def valid_routes(valid_topology, valid_streams):
    return {
        "delay_units": "us",
        "routes": [{
            "flow_id": 0,
            "paths": [[
                {"node": "ES0", "port": 0},
                {"node": "SW0", "port": 1},
                {"node": "SW1", "port": 1},
                {"node": "ES1", "port": 0}
            ]],
            "min_e2e_delay": 10.0
        },{
            "flow_id": 1,
            "paths": [[
                {"node": "ES0", "port": 0},
                {"node": "SW0", "port": 1},
                {"node": "SW1", "port": 1},
                {"node": "ES1", "port": 0}
            ]],
             "min_e2e_delay": 0.0 
        },{
            "flow_id": 2, 
            "paths": [[
                {"node": "ES0", "port": 0},
                {"node": "SW0", "port": 1},
                {"node": "SW1", "port": 1},
                {"node": "ES1", "port": 0}
            ]],
             "min_e2e_delay": 10.0
        }]
    }

@pytest.fixture
def valid_gen_config():
     return {
        "delay_units": "MICRO_SECOND",
        "general": {"output_directory": "out", "num_test_cases": 1,
                    "topology_size": {"num_switches": 1, "num_end_systems": 1}},
        "network": {"topology_type": "mesh_graph", "parameters": "{'n':1,'m':1}"},
        "traffic": {"types": [{
            "name": "ISO", "number": 1, "PCP-list": [7],
            "min_packet_size": 64, "max_packet_size": 128,
            "cycle_time": {"cycle_time_list": [1000]}, 
            "min_delay": 100, "max_delay": 900, 
            "redundancy": 0 
            }]},
     }


# --- Test Topology Validation ---

def test_validate_topology_valid(valid_topology):
    errors = validate_topology(valid_topology)
    assert not errors 

def test_validate_topology_invalid_schema(valid_topology):
    invalid_topo = copy.deepcopy(valid_topology) 
    del invalid_topo["topology"]["switches"] 
    errors = validate_topology(invalid_topo)
    assert len(errors) > 0
    assert "'switches' is a required property" in errors[0] 

def test_validate_topology_invalid_integrity_link_node(valid_topology):
    invalid_topo = copy.deepcopy(valid_topology)
    invalid_topo["topology"]["links"].append(
         {"id": "LX", "source": "SW0", "destination": "SW_NONEXIST", "sourcePort": 2, "destinationPort": 0, "domain": 0}
    )
    errors = validate_topology(invalid_topo)
    assert len(errors) > 0
    assert "references non-existent destination node SW_NONEXIST" in errors[0]

def test_validate_topology_duplicate_link_id(valid_topology):
    invalid_topo = copy.deepcopy(valid_topology)
    invalid_topo["topology"]["links"].append(
        {"id": "L0", "source": "SW0", "destination": "SW1", "sourcePort": 2, "destinationPort": 1, "domain": 0}
    )
    errors = validate_topology(invalid_topo)
    assert len(errors) > 0
    assert "Duplicate link IDs found" in errors[0]

def test_validate_topology_missing_switch_ports_field(valid_topology):
    invalid_topo = copy.deepcopy(valid_topology)
    del invalid_topo["topology"]["switches"][0]["ports"]
    errors = validate_topology(invalid_topo)

    assert len(errors) > 0
    assert "'ports' is a required property" in errors[0]



# --- Test Streams Validation ---

def test_validate_streams_valid(valid_streams):
    errors = validate_streams(valid_streams)
    assert not errors

def test_validate_streams_invalid_schema(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][0]["PCP"] = 9
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "Stream 0 has invalid PCP value 9" in errors[0]

def test_validate_streams_best_effort_invalid_period(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][1]["period"] = 1000 
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "BEST-EFFORT, but period should be None" in errors[0]

def test_validate_streams_best_effort_invalid_deadline(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][1]["destinations"][0]["deadline"] = 500 
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "Stream S1 has type BEST-EFFORT, but destination ES1 has a deadline." in errors[0]

def test_validate_streams_audio_voice_invalid_period(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][2]["period"] = 1000 
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "AUDIO/VOICE, but period should be None" in errors[0]

def test_validate_streams_audio_voice_missing_deadline(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][2]["destinations"][0]["deadline"] = None 
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "does not have a valid deadline" in errors[0]

def test_validate_streams_other_type_missing_period(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][0]["period"] = None
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "does not have a valid period" in errors[0]

def test_validate_streams_other_type_missing_deadline(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][2]["destinations"][0]["deadline"] = None
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "does not have a valid deadline" in errors[0]

def test_validate_streams_duplicate_stream_id(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"].append({ 
        "id": 0,
        "name": "S_Dup",
        "source": "ES0",
        "destinations": [{"id": "ES1", "deadline": 500}],
        "type": "ISOCHRONOUS",
        "PCP": 7,
        "size": 100,
        "period": 1000,
        "redundancy": 0
    })
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "Duplicate stream IDs found" in errors[0]

def test_validate_streams_no_destinations(valid_streams):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][0]["destinations"] = []
    errors = validate_streams(invalid_streams)
    assert len(errors) > 0
    assert "Stream 0 has no destinations" in errors[0]


# --- Test Routes Validation ---

def test_validate_routes_valid(valid_routes, valid_topology, valid_streams):
     errors = validate_routes(valid_routes, valid_topology, valid_streams)
     assert not errors, f"Validation failed with errors: {errors}" 

def test_validate_routes_invalid_schema(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)
    del invalid_routes["routes"][0]["paths"] 
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) > 0
    assert "'paths' is a required property" in errors[0]

def test_validate_routes_missing_stream_route(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)
    invalid_routes["routes"] = [r for r in invalid_routes["routes"] if r["flow_id"] == 0]
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) == 2
    error_msgs = [str(e) for e in errors]
    assert "Stream S1 (ID 1) does not have a route" in error_msgs
    assert "Stream S2 (ID 2) does not have a route" in error_msgs

def test_validate_routes_invalid_node_in_path(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)
    invalid_routes["routes"][0]["paths"][0].insert(1, {"node": "NODE_X", "port": 0})
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) > 0
    assert "references non-existent node NODE_X" in errors[0]

def test_validate_routes_path_does_not_start_at_source(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)
    invalid_routes["routes"][0]["paths"][0][0]["node"] = "SW0"
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) > 0
    assert "Route for stream S0 does not start at source ES0" in errors[0]

def test_validate_routes_end_system_uses_non_zero_port(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)
    invalid_routes["routes"][0]["paths"][0][0]["port"] = 1 
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) > 0
    assert "End system ES0 in route for stream S0 uses invalid port 1, should be 0" in errors[0]

def test_validate_routes_switch_port_out_of_bounds(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)
    invalid_routes["routes"][0]["paths"][0][1]["port"] = 4
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) > 0
    assert "Switch SW0 in route for stream S0 uses port 4, but only has 4 ports" in errors[0]

def test_validate_routes_no_link_between_hops(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)
    invalid_routes["routes"][0]["paths"][0] = [{"node": "ES0", "port": 0}, {"node": "ES1", "port": 0}]
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) > 0
    assert "No link exists between ES0 and ES1 in route for stream S0" in errors[0]

def test_validate_routes_port_mismatch_on_link(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)

    invalid_routes["routes"][0]["paths"][0][1]["port"] = 2
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) > 0
    assert "Route for stream S0 uses port 2 on node SW0, but link L2 uses port 1" in errors[0]

def test_validate_routes_empty_path_in_paths(valid_routes, valid_topology, valid_streams):
    invalid_routes = copy.deepcopy(valid_routes)
    invalid_routes["routes"][0]["paths"].append([])
    errors = validate_routes(invalid_routes, valid_topology, valid_streams)
    assert len(errors) > 0
    assert "Empty path found for stream S0" in errors[0]


# --- Test Gen Config Validation ---

def test_validate_gen_config_valid(valid_gen_config):
    errors = validate_gen_config(valid_gen_config)
    assert not errors

def test_validate_gen_config_invalid_schema(valid_gen_config):
    invalid_config = copy.deepcopy(valid_gen_config)
    del invalid_config["network"]
    errors = validate_gen_config(invalid_config)
    assert len(errors) > 0
    assert "'network' is a required property" in errors[0]

# --- Test validate_all ---

def test_validate_all_valid(valid_topology, valid_streams, valid_routes):
    errors = validate_all(valid_topology, valid_streams, valid_routes)
    assert not errors

def test_validate_all_valid_no_routes(valid_topology, valid_streams):
    errors = validate_all(valid_topology, valid_streams) 
    assert not errors

def test_validate_all_invalid_topology(valid_topology, valid_streams, valid_routes):
    invalid_topo = copy.deepcopy(valid_topology)
    del invalid_topo["topology"]["switches"]
    errors = validate_all(invalid_topo, valid_streams, valid_routes)
    assert len(errors) > 0
    assert "'switches' is a required property" in errors[0]

def test_validate_all_invalid_streams(valid_topology, valid_streams, valid_routes):
    invalid_streams = copy.deepcopy(valid_streams)
    invalid_streams["streams"][0]["PCP"] = 9 
    errors = validate_all(valid_topology, invalid_streams, valid_routes)
    assert len(errors) > 0
    assert "Stream 0 has invalid PCP value 9" in errors[0]

def test_validate_all_invalid_routes(valid_topology, valid_streams, valid_routes):
    invalid_routes = copy.deepcopy(valid_routes)
    invalid_routes["routes"][0]["paths"][0].append({"node": "NODE_X", "port": 0}) 
    errors = validate_all(valid_topology, valid_streams, invalid_routes)
    assert len(errors) > 0
    assert "references non-existent node NODE_X" in errors[0] 