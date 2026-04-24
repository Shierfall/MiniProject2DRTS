from tsn_case_gen_.app.tsn_case_gen import TSNTestCaseGenerator
import json

def test_topology_stream_integration(tsn_generator):
    #Test integration between topology and stream generation.
    # Generate topology
    topology_data = tsn_generator.generate_topology()
    
    # Generate streams based on topology
    streams = tsn_generator.generate_streams(topology_data)
    
    # Verify that streams reference valid nodes from topology
    topology_nodes = set()
    for switch in topology_data["switches"]:
        topology_nodes.add(switch["id"])
    for end_system in topology_data["end_systems"]:
        topology_nodes.add(end_system["id"])
    
    for stream in streams["streams"]:
        assert stream["source"] in topology_nodes, f"Stream {stream['id']} references invalid source node"
        for dest in stream["destinations"]:
            assert dest["id"] in topology_nodes, f"Stream {stream['id']} references invalid destination node"

def test_stream_route_integration(tsn_generator):
    #Test integration between stream generation and routing.
    # Generate topology and streams
    topology_data = tsn_generator.generate_topology()
    streams = tsn_generator.generate_streams(topology_data)
    
    # Generate routes
    routes = tsn_generator.generate_routes(topology_data, streams)
    
    # Verify that routes exist for all streams
    for stream in streams["streams"]:
        stream_id = stream["id"]
        # Find the route for this stream
        matching_routes = [r for r in routes["routes"] if r["flow_id"] == stream_id]
        assert len(matching_routes) > 0, f"No route found for stream {stream_id}"
        
        route = matching_routes[0]
        assert "paths" in route, f"No paths in route for stream {stream_id}"
        
        # Verify that paths connect source to destinations
        for path in route["paths"]:
            assert len(path) > 0, f"Empty path for stream {stream_id}"
            assert path[0]["node"] == stream["source"], f"Path doesn't start at source for stream {stream_id}"
            assert path[-1]["node"] in [dest["id"] for dest in stream["destinations"]], f"Path doesn't end at destination for stream {stream_id}"

def test_cross_domain_integration(tsn_generator, basic_config, config_file):
    #Test integration of cross-domain functionality.
    basic_config["general"]["num_domains"] = 2
    basic_config["general"]["cross_domain_streams"] = 2
    basic_config["domain_connections"] = {
        "type": "line",
        "connections_per_domain_pair": 1
    }
    
    # Write updated config to file
    with open(config_file, 'w') as f:
        json.dump(basic_config, f)
    
    # Create a new generator with the updated config
    tsn_generator = TSNTestCaseGenerator(config_file, seed=42)
    
    # Generate test case
    topology_data = tsn_generator.generate_topology()
    streams = tsn_generator.generate_streams(topology_data)
    routes = tsn_generator.generate_routes(topology_data, streams)
    
    # Verify domain structure
    domains = set()
    for switch in topology_data["switches"]:
        domains.add(switch["domain"])
        assert "id" in switch, "Switch missing id"
        assert "ports" in switch, "Switch missing ports"
        assert "domain" in switch, "Switch missing domain"
    
    assert len(domains) == 2, "Expected 2 domains in topology"
    
    # Verify cross-domain streams
    cross_domain_count = 0
    for stream in streams["streams"]:
        source_domain = None
        dest_domain = None
        
        # Find source domain
        for node in topology_data["switches"] + topology_data["end_systems"]:
            if node["id"] == stream["source"]:
                source_domain = node["domain"]
                break
                
        # Find destination domain
        for dest in stream["destinations"]:
            for node in topology_data["switches"] + topology_data["end_systems"]:
                if node["id"] == dest:
                    dest_domain = node["domain"]
                    break
            if source_domain != dest_domain:
                cross_domain_count += 1
                break
    
    assert cross_domain_count >= 2, "Not enough cross-domain streams generated" 