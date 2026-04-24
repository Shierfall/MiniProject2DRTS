import os
import json
from tsn_case_gen_.app.tsn_case_gen import TSNTestCaseGenerator

def test_basic_end_to_end_generation(tsn_generator, test_output_dir):
    #Test basic end-to-end generation of a test case.
    # Generate test cases
    tsn_generator.generate_test_cases()
    
    # Check if output directory exists
    test_case_dir = os.path.join(test_output_dir, "test_case_1")
    assert os.path.exists(test_case_dir), "Test case directory was not created"
    
    # Check if all required files were generated
    required_files = ["topology.json", "streams.json", "routes.json"]
    for file in required_files:
        file_path = os.path.join(test_case_dir, file)
        assert os.path.exists(file_path), f"{file} was not generated"
    
    # Load and validate the generated files
    with open(os.path.join(test_case_dir, "topology.json")) as f:
        topology_data = json.load(f)
    with open(os.path.join(test_case_dir, "streams.json")) as f:
        json.load(f)
    with open(os.path.join(test_case_dir, "routes.json")) as f:
        json.load(f)
    
    # Get the actual topology from the nested structure
    topology = topology_data["topology"]
    
    # Verify basic topology structure
    assert "delay_units" in topology, "Topology missing delay_units"
    assert "switches" in topology, "Topology missing switches"
    assert "end_systems" in topology, "Topology missing end systems"
    assert "links" in topology, "Topology missing links"
    
    # Verify that all nodes have the required fields
    for switch in topology["switches"]:
        assert "id" in switch, "Switch missing id"
        assert "domain" in switch, "Switch missing domain"
        assert "ports" in switch, "Switch missing ports"
        
    for end_system in topology["end_systems"]:
        assert "id" in end_system, "End system missing id"
        assert "domain" in end_system, "End system missing domain"
        
    for link in topology["links"]:
        assert "id" in link, "Link missing id"
        assert "source" in link, "Link missing source"
        assert "destination" in link, "Link missing destination"
        assert "sourcePort" in link, "Link missing sourcePort"
        assert "destinationPort" in link, "Link missing destinationPort"

def test_multiple_test_cases(tsn_generator, test_output_dir, basic_config, config_file):
    #Test generation of multiple test cases.
    basic_config["general"]["num_test_cases"] = 3
    basic_config["general"]["output_directory"] = test_output_dir
    
    # Write updated config to file
    with open(config_file, 'w') as f:
        json.dump(basic_config, f)
    
    # Create a new generator with the updated config
    tsn_generator = TSNTestCaseGenerator(config_file, seed=42)
    tsn_generator.generate_test_cases()
    
    # Check if all test case directories were created
    for i in range(1, 4):
        test_case_dir = os.path.join(test_output_dir, f"test_case_{i}")
        assert os.path.exists(test_case_dir), f"Test case {i} directory was not created"
        
        # Verify files in each test case
        required_files = ["topology.json", "streams.json", "routes.json"]
        for file in required_files:
            file_path = os.path.join(test_case_dir, file)
            assert os.path.exists(file_path), f"{file} was not generated in test case {i}"
            
            # Verify file structure
            with open(file_path) as f:
                data = json.load(f)
                if file == "topology.json":
                    topology = data["topology"]
                    assert "delay_units" in topology, f"Topology in test case {i} missing delay_units"
                    assert "switches" in topology, f"Topology in test case {i} missing switches"
                    assert "end_systems" in topology, f"Topology in test case {i} missing end systems"
                    assert "links" in topology, f"Topology in test case {i} missing links"
                elif file == "streams.json":
                    assert "delay_units" in data, f"Streams in test case {i} missing delay_units"
                    assert "streams" in data, f"Streams in test case {i} missing streams array"
                elif file == "routes.json":
                    assert "delay_units" in data, f"Routes in test case {i} missing delay_units"
                    assert "routes" in data, f"Routes in test case {i} missing routes array"
                    for route in data["routes"]:
                        assert "flow_id" in route, f"Route in test case {i} missing flow_id"
                        assert "paths" in route, f"Route in test case {i} missing paths"
                        assert "min_e2e_delay" in route, f"Route in test case {i} missing min_e2e_delay" 