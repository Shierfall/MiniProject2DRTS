import json
from tsn_case_gen_.app.tsn_case_gen import TSNTestCaseGenerator

def test_different_topology_types(tsn_generator, basic_config, config_file):
    #Test generation with different topology types.
    topology_configs = [
        ("mesh_graph", "{'n': 3, 'm': 2}"),
        ("industrial_ring_graph", "{'cwsg_num_rings': 2}"),
        ("tree_graph", "{'r': 2, 'h': 2}"),
        ("binomial_graph", "{'p': 0.3}"),
        ("random_geometric_graph", "{'r': 0.5}")
    ]

    for topology_type, params in topology_configs:
        # Modify config for current topology type
        basic_config["general"]["topology_type"] = topology_type
        basic_config["general"]["parameters"] = params
        basic_config["network"]["topology_type"] = topology_type
        basic_config["network"]["parameters"] = params
        # Set num_switches based on topology type
        if topology_type == "mesh_graph" or topology_type == "industrial_ring_graph":
            basic_config["general"]["topology_size"]["num_switches"] = 6
        elif topology_type == "tree_graph":
            basic_config["general"]["topology_size"]["num_switches"] = 7
        else:
            basic_config["general"]["topology_size"]["num_switches"] = 4

        # Write updated config to file
        with open(config_file, 'w') as f:
            json.dump(basic_config, f)
        
        # Create a new generator with the updated config
        tsn_generator = TSNTestCaseGenerator(config_file, seed=42)
        
        # Generate test case
        topology_data = tsn_generator.generate_topology()
        
        # Verify basic topology structure
        assert "delay_units" in topology_data, "Topology missing delay_units"
        assert "switches" in topology_data, "Topology missing switches"
        assert "end_systems" in topology_data, "Topology missing end systems"
        assert "links" in topology_data, "Topology missing links"
        
        # Verify that we have the expected number of nodes
        assert len(topology_data["switches"]) > 0, f"No switches generated for {topology_type}"
        assert len(topology_data["end_systems"]) > 0, f"No end systems generated for {topology_type}"
        assert len(topology_data["links"]) > 0, f"No links generated for {topology_type}"
        
        # Verify that all nodes have the required fields
        for switch in topology_data["switches"]:
            assert "id" in switch, "Switch missing id"
            assert "domain" in switch, "Switch missing domain"
            assert "ports" in switch, "Switch missing ports"
            
        for end_system in topology_data["end_systems"]:
            assert "id" in end_system, "End system missing id"
            assert "domain" in end_system, "End system missing domain"
            
        for link in topology_data["links"]:
            assert "id" in link, "Link missing id"
            assert "source" in link, "Link missing source"
            assert "destination" in link, "Link missing destination"
            assert "sourcePort" in link, "Link missing sourcePort"
            assert "destinationPort" in link, "Link missing destinationPort"

def test_different_traffic_patterns(tsn_generator, basic_config, config_file):
    #Test generation with different traffic patterns.
    traffic_types = [
        {
            "name": "ISOCHRONOUS",
            "PCP-list": [7],
            "number": 5,
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
        },
        {
            "name": "BEST-EFFORT",
            "PCP-list": [0],
            "number": 5,
            "redundant_number": 0,
            "redundant_routes": 0,
            "min_delay": 100,
            "max_delay": 1000,
            "min_packet_size": 64,
            "max_packet_size": 1500,
            "bidirectional": True
        }
    ]
    
    for traffic_type in traffic_types:
        # Modify config for current traffic pattern
        basic_config["traffic"]["types"] = [traffic_type]
        
        # Write updated config to file
        with open(config_file, 'w') as f:
            json.dump(basic_config, f)
        
        # Create a new generator with the updated config
        tsn_generator = TSNTestCaseGenerator(config_file, seed=42)
        
        # Generate test case
        topology_data = tsn_generator.generate_topology()
        streams = tsn_generator.generate_streams(topology_data)
        
        # Verify streams were generated
        assert "streams" in streams, "No streams array in output"
        
        # For bidirectional streams, we expect twice the number of streams
        expected_streams = traffic_type["number"] * (2 if traffic_type["bidirectional"] else 1)
        assert len(streams["streams"]) == expected_streams, \
            f"Expected {expected_streams} streams for {traffic_type['name']}"
        
        # Verify stream properties
        for stream in streams["streams"]:
            assert "id" in stream, "Stream missing id"
            assert "source" in stream, "Stream missing source"
            assert "destinations" in stream, "Stream missing destinations"
            assert "size" in stream, "Stream missing size"
            assert stream["size"] >= traffic_type["min_packet_size"], "Stream size below minimum"
            assert stream["size"] <= traffic_type["max_packet_size"], "Stream size above maximum"

def test_different_network_sizes(tsn_generator, basic_config, config_file):
    #Test generation with different network sizes.
    network_sizes = [
        {"num_switches": 4, "num_end_systems": 8, "end_systems_per_switch": [0, 4]},
        {"num_switches": 4, "num_end_systems": 12, "end_systems_per_switch": [0, 4]},
        {"num_switches": 4, "num_end_systems": 16, "end_systems_per_switch": [0, 4]}
    ]
    
    for size in network_sizes:
        # Modify config for current network size
        basic_config["general"]["topology_size"] = size
        
        # Write updated config to file
        with open(config_file, 'w') as f:
            json.dump(basic_config, f)
        
        # Create a new generator with the updated config
        tsn_generator = TSNTestCaseGenerator(config_file, seed=42)
        
        # Generate test case
        topology_data = tsn_generator.generate_topology()
        
        # Verify node counts
        assert len(topology_data["switches"]) == size["num_switches"], \
            f"Expected {size['num_switches']} switches, got {len(topology_data['switches'])}"
        assert len(topology_data["end_systems"]) == size["num_end_systems"], \
            f"Expected {size['num_end_systems']} end systems, got {len(topology_data['end_systems'])}"
        
        # Verify end systems per switch
        for switch in topology_data["switches"]:
            connected_end_systems = sum(1 for link in topology_data["links"] 
                                     if link["source"] == switch["id"] and 
                                     any(es["id"] == link["destination"] for es in topology_data["end_systems"]))
            assert size["end_systems_per_switch"][0] <= connected_end_systems <= size["end_systems_per_switch"][1], \
                f"Switch {switch['id']} has {connected_end_systems} end systems, expected between {size['end_systems_per_switch']}" 