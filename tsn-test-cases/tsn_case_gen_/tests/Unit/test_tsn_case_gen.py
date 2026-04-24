import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch
from tsn_case_gen_.app.tsn_case_gen import TSNTestCaseGenerator
import sys



# --- Fixtures --- 

@pytest.fixture
def minimal_valid_config_dict():
    """Provides a minimal valid configuration dictionary for testing."""
    return {
        "delay_units": "MICRO_SECOND",
        "general": {
            "output_directory": "test_output",
            "num_test_cases": 1,
            "topology_size": {
                "num_switches": 1,
                "num_end_systems": 1,
                "end_systems_per_switch": [1]
            },
            "test_case_naming": "case_{}",
            "generate_routes": True,
        },
        "network": {
            "topology_type": "mesh_graph",
            "parameters": "{'n':1, 'm':1}",
            "default_bandwidth_mbps": 1000
        },
        "traffic": {
            "types": [
                {
                    "name": "ISO",
                    "number": 1,
                    "PCP-list": [7],
                    "min_packet_size": 64, "max_packet_size": 128,
                    "cycle_time": {"cycle_time_list": [1000]},
                    "min_delay": 100, "max_delay": 900
                 }
             ]
        }
    }

@pytest.fixture
def mock_config_file(tmp_path, minimal_valid_config_dict):
    """Creates a temporary valid config JSON file using tmp_path fixture."""
    config_path = tmp_path / "test_gen_config.json"
    config_path.write_text(json.dumps(minimal_valid_config_dict))
    return config_path

@pytest.fixture
def mock_invalid_json_file(tmp_path):
    """Creates a temporary invalid (malformed JSON) config file."""
    config_path = tmp_path / "invalid_config.json"
    config_path.write_text("{ 'invalid_json': ")
    return config_path

# --- Test _load_config --- 

def test_load_config_valid(mocker, mock_config_file, minimal_valid_config_dict):
    """Test TSNTestCaseGenerator initialization with a valid config file."""
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    mocker.patch('os.makedirs')

    generator = TSNTestCaseGenerator(config_path=mock_config_file)

    assert generator.config == minimal_valid_config_dict

def test_load_config_invalid_json(mock_invalid_json_file):
    """Test TSNTestCaseGenerator initialization with invalid JSON config."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        TSNTestCaseGenerator(config_path=mock_invalid_json_file)

def test_load_config_validation_error(mocker, mock_config_file):
    """Test TSNTestCaseGenerator initialization when config fails schema validation."""
    validation_errors = ["Schema error: missing 'network' section"]
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=validation_errors)
    mocker.patch('os.makedirs')

    with pytest.raises(ValueError, match="Invalid configuration"):
        TSNTestCaseGenerator(config_path=mock_config_file)

def test_load_config_file_not_found():
    """Test TSNTestCaseGenerator initialization with a non-existent config file."""
    non_existent_path = Path("non_existent_config.json")
    with pytest.raises(ValueError, match="Error loading configuration"):
        TSNTestCaseGenerator(config_path=non_existent_path)


# --- Test __init__ --- 
def test_init_seed(mocker, mock_config_file):
    """Test if random.seed is called when a seed is provided."""
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    mocker.patch('os.makedirs')
    mock_seed = mocker.patch('random.seed')

    seed_value = 12345
    TSNTestCaseGenerator(config_path=mock_config_file, seed=seed_value)

    mock_seed.assert_called_once_with(seed_value)

def test_init_makedirs(mocker, mock_config_file, minimal_valid_config_dict):
    """Test if os.makedirs is called to create the output directory."""
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    mock_makedirs = mocker.patch('os.makedirs')

    TSNTestCaseGenerator(config_path=mock_config_file)

    expected_dir = minimal_valid_config_dict["general"]["output_directory"]
    mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)

# --- Test generate_test_cases ---

def test_generate_test_cases_calls_components(mocker, mock_config_file, minimal_valid_config_dict):
    """Test the main loop calls generation, validation, and writing methods."""
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    mock_makedirs = mocker.patch('os.makedirs')

    mock_gen_topo = mocker.patch.object(TSNTestCaseGenerator, 'generate_topology', return_value={"topology": {}})
    mock_gen_streams = mocker.patch.object(TSNTestCaseGenerator, 'generate_streams', return_value={"streams": []})
    mock_gen_routes = mocker.patch.object(TSNTestCaseGenerator, 'generate_routes', return_value={"routes": []})
    mock_validate_all = mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_all', return_value=[])
    mock_write_topo = mocker.patch.object(TSNTestCaseGenerator, 'write_topology')
    mock_write_streams = mocker.patch.object(TSNTestCaseGenerator, 'write_streams')
    mock_write_routes = mocker.patch.object(TSNTestCaseGenerator, 'write_routes')

    num_cases = 3
    minimal_valid_config_dict["general"]["num_test_cases"] = num_cases
    mock_config_file.write_text(json.dumps(minimal_valid_config_dict))

    generator = TSNTestCaseGenerator(config_path=mock_config_file)
    generator.generate_test_cases()

    assert mock_gen_topo.call_count == num_cases
    assert mock_gen_streams.call_count == num_cases
    assert mock_gen_routes.call_count == num_cases
    assert mock_validate_all.call_count == num_cases
    assert mock_write_topo.call_count == num_cases
    assert mock_write_streams.call_count == num_cases
    assert mock_write_routes.call_count == num_cases
    assert mock_makedirs.call_count == 1 + num_cases

def test_custom_naming_pattern_used(mocker, mock_config_file, minimal_valid_config_dict):
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    mock_makedirs = mocker.patch('os.makedirs')

    minimal_valid_config_dict["general"]["num_test_cases"] = 1
    minimal_valid_config_dict["general"]["test_case_naming"] = "custom_case_{}"
    mock_config_file.write_text(json.dumps(minimal_valid_config_dict))

    mocker.patch.object(TSNTestCaseGenerator, 'generate_topology', return_value={})
    mocker.patch.object(TSNTestCaseGenerator, 'generate_streams', return_value={"streams": [], "delay_units": "MICRO_SECOND"})
    mocker.patch.object(TSNTestCaseGenerator, 'generate_routes', return_value={"routes": [], "delay_units": "MICRO_SECOND"})
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_all', return_value=[])
    mocker.patch.object(TSNTestCaseGenerator, 'write_topology')
    mocker.patch.object(TSNTestCaseGenerator, 'write_streams')
    mocker.patch.object(TSNTestCaseGenerator, 'write_routes')

    generator = TSNTestCaseGenerator(config_path=mock_config_file)
    generator.generate_test_cases()

    expected_dir_name = os.path.join(minimal_valid_config_dict["general"]["output_directory"], "custom_case_1")
    assert any(expected_dir_name in str(call[0][0]) for call in mock_makedirs.call_args_list)

# --- Test _write_topology ---
def test_write_topology_creates_valid_json(mocker, tmp_path):
    mock_topology = {"nodes": [{"id": "switch1"}], "links": []}
    output_dir = tmp_path
    generator = TSNTestCaseGenerator.__new__(TSNTestCaseGenerator)
    
    output_file = output_dir / "topology.json"
    generator.write_topology(mock_topology, str(output_dir))

    with open(output_file, 'r') as f:
        content = json.load(f)
    
    assert "topology" in content
    assert content["topology"]["nodes"][0]["id"] == "switch1"

def test_write_streams_creates_valid_json(mocker, tmp_path):
    mock_streams = {
        "delay_units": "MICRO_SECOND",
        "streams": [
            {"id": "stream1", "source": "es1", "destination": "es2"},
            {"id": "stream2", "source": "es3", "destination": "es4"}
        ]
    }
    output_dir = tmp_path
    generator = TSNTestCaseGenerator.__new__(TSNTestCaseGenerator)

    output_file = output_dir / "streams.json"
    generator.write_streams(mock_streams, str(output_dir))

    with open(output_file, 'r') as f:
        content = json.load(f)

    assert "delay_units" in content
    assert len(content["streams"]) == 2
    assert content["streams"][0]["id"] == "stream1"

# --- Test _generate_routes ---

def test_generate_routes_none_skips_write_routes(mocker, mock_config_file):
    """Test that write_routes is not called when _generate_routes returns None."""
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    mocker.patch('os.makedirs')

    mocker.patch.object(TSNTestCaseGenerator, 'generate_topology', return_value={})
    mocker.patch.object(TSNTestCaseGenerator, 'generate_streams', return_value={"streams": [], "delay_units": "MICRO_SECOND"})
    mocker.patch.object(TSNTestCaseGenerator, 'generate_routes', return_value=None)
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_all', return_value=[])
    mock_write_topo = mocker.patch.object(TSNTestCaseGenerator, 'write_topology')
    mock_write_streams = mocker.patch.object(TSNTestCaseGenerator, 'write_streams')
    mock_write_routes = mocker.patch.object(TSNTestCaseGenerator, 'write_routes')

    generator = TSNTestCaseGenerator(config_path=mock_config_file)
    generator.generate_test_cases()

    mock_write_topo.assert_called_once()
    mock_write_streams.assert_called_once()
    mock_write_routes.assert_not_called()

def test_generate_routes_passes_config_flags(mocker, mock_config_file, minimal_valid_config_dict):
    """Test that _generate_routes is called with the correct configuration flags."""
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    mocker.patch('os.makedirs')

    minimal_valid_config_dict["routing"] = {
        "consider_link_utilization": True,
        "algorithm": "custom_algorithm"
    }
    mock_config_file.write_text(json.dumps(minimal_valid_config_dict))

    mocker.patch.object(TSNTestCaseGenerator, 'generate_topology', return_value={})
    mocker.patch.object(TSNTestCaseGenerator, 'generate_streams', return_value={"streams": [], "delay_units": "MICRO_SECOND"})
    mock_gen_routes = mocker.patch.object(TSNTestCaseGenerator, 'generate_routes', return_value={"routes": [], "delay_units": "MICRO_SECOND"})
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_all', return_value=[])
    mocker.patch.object(TSNTestCaseGenerator, 'write_topology')
    mocker.patch.object(TSNTestCaseGenerator, 'write_streams')
    mocker.patch.object(TSNTestCaseGenerator, 'write_routes')

    generator = TSNTestCaseGenerator(config_path=mock_config_file)
    generator.generate_test_cases()

    mock_gen_routes.assert_called_once()
    args, kwargs = mock_gen_routes.call_args
    assert len(args) == 2  # topology and streams

# --- Test generate_topology ---

def test_generate_topology_creates_valid_structure(mocker, mock_config_file, minimal_valid_config_dict):
    """Test that generate_topology creates a valid topology structure."""
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    
    # Mock the TopologyGenerator
    mock_topology_generator = mocker.patch('tsn_case_gen_.app.tsn_case_gen.TopologyGenerator')
    mock_instance = mock_topology_generator.return_value
    mock_instance.generate.return_value = {
        "delay_units": "MICRO_SECOND",
        "default_bandwidth_mbps": 1000,
        "switches": [{"id": "SW0", "ports": 8, "domain": 0}],
        "end_systems": [{"id": "ES0", "domain": 0}],
        "links": [{"id": "Link0", "source": "SW0", "destination": "ES0", "sourcePort": 1, "destinationPort": 1}]
    }
    
    generator = TSNTestCaseGenerator(config_path=mock_config_file)
    topology = generator.generate_topology()
    
    # Verify the structure
    assert "delay_units" in topology
    assert "default_bandwidth_mbps" in topology
    assert "switches" in topology
    assert "end_systems" in topology
    assert "links" in topology
    assert len(topology["switches"]) == 1
    assert len(topology["end_systems"]) == 1
    assert len(topology["links"]) == 1
    
    # Verify TopologyGenerator was called with correct parameters
    args, kwargs = mock_topology_generator.call_args
    assert kwargs["num_switches"] == 1
    assert kwargs["num_end_systems"] == 1
    assert kwargs["end_systems_per_switch"] == [1]
    assert kwargs["topology_type"] == "mesh_graph"
    assert kwargs["topology_params"] == "{'n':1, 'm':1}"
    assert kwargs["default_bandwidth_mbps"] == 1000

def test_generate_topology_passes_config_parameters(mocker, mock_config_file, minimal_valid_config_dict):
    """Test that generate_topology passes configuration parameters correctly."""
    mocker.patch('tsn_case_gen_.app.tsn_case_gen.validate_gen_config', return_value=[])
    
    # Add domain connection parameters
    minimal_valid_config_dict["domain_connections"] = {
        "type": "line",
        "connections_per_domain_pair": 2
    }
    minimal_valid_config_dict["general"]["num_domains"] = 2
    mock_config_file.write_text(json.dumps(minimal_valid_config_dict))
    
    mock_topology_generator = mocker.patch('tsn_case_gen_.app.tsn_case_gen.TopologyGenerator')
    mock_instance = mock_topology_generator.return_value
    mock_instance.generate.return_value = {"switches": [], "end_systems": [], "links": []}
    
    generator = TSNTestCaseGenerator(config_path=mock_config_file)
    generator.generate_topology()
    

    args, kwargs = mock_topology_generator.call_args
    assert kwargs["num_domains"] == 2
    assert kwargs["domain_connection_type"] == "line"
    assert kwargs["connections_per_domain_pair"] == 2

# --- Test write_routes ---

def test_write_routes_creates_valid_json(mocker, tmp_path):
    """Test that write_routes creates a valid JSON file with correct structure."""
    mock_routes = {
        "delay_units": "MICRO_SECOND",
        "routes": [
            {
                "stream_id": 0,
                "paths": [
                    [
                        {"node": "ES0", "port": 0},
                        {"node": "SW0", "port": 1},
                        {"node": "ES1", "port": 0}
                    ]
                ]
            }
        ]
    }
    
    output_dir = tmp_path
    generator = TSNTestCaseGenerator.__new__(TSNTestCaseGenerator)
    generator.write_routes(mock_routes, str(output_dir))
    
    output_file = output_dir / "routes.json"
    assert output_file.exists()
    
    with open(output_file, 'r') as f:
        content = json.load(f)
    
    assert "delay_units" in content
    assert "routes" in content
    assert len(content["routes"]) == 1
    assert content["routes"][0]["stream_id"] == 0
    assert len(content["routes"][0]["paths"]) == 1
    assert len(content["routes"][0]["paths"][0]) == 3

def test_write_routes_handles_empty_routes(mocker, tmp_path):
    """Test that write_routes handles empty routes correctly."""
    mock_routes = {
        "delay_units": "MICRO_SECOND",
        "routes": []
    }
    
    output_dir = tmp_path
    generator = TSNTestCaseGenerator.__new__(TSNTestCaseGenerator)
    generator.write_routes(mock_routes, str(output_dir))
    
    output_file = output_dir / "routes.json"
    assert output_file.exists()
    
    with open(output_file, 'r') as f:
        content = json.load(f)
    
    assert "delay_units" in content
    assert "routes" in content
    assert len(content["routes"]) == 0



def test_main_runs_with_config(monkeypatch):
    # Simulate command-line arguments: --config provided
    monkeypatch.setattr(sys, "argv", ["tsn_case_gen.py", "--config", "dummy_config.json"])
    with patch("tsn_case_gen_.app.tsn_case_gen.TSNTestCaseGenerator") as MockGen, \
         patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
        instance = MockGen.return_value
        instance.generate_test_cases.return_value = None
        from tsn_case_gen_.cli import main
        main()
        mock_exit.assert_not_called()
        assert instance.generate_test_cases.called


def test_main_runs_with_default_config(monkeypatch):
    # Simulate command-line arguments: no --config, but default config exists
    monkeypatch.setattr(sys, "argv", ["tsn_case_gen.py"])
    with patch("os.path.exists", return_value=True), \
         patch("tsn_case_gen_.app.tsn_case_gen.TSNTestCaseGenerator") as MockGen, \
         patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
        instance = MockGen.return_value
        instance.generate_test_cases.return_value = None
        from tsn_case_gen_.cli import main
        main()
        mock_exit.assert_not_called()
        assert instance.generate_test_cases.called


def test_main_exits_if_no_config(monkeypatch):
    # Simulate command-line arguments: no --config, and default config does not exist
    monkeypatch.setattr(sys, "argv", ["tsn_case_gen.py"])
    with patch("os.path.exists", return_value=False), \
         patch("sys.exit", side_effect=SystemExit(1)):
        from tsn_case_gen_.cli import main
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_main_exits_on_exception(monkeypatch):
    # Simulate command-line arguments: --config provided, but generator throws
    monkeypatch.setattr(sys, "argv", ["tsn_case_gen.py", "--config", "dummy_config.json"])
    with patch("tsn_case_gen_.app.tsn_case_gen.TSNTestCaseGenerator", side_effect=Exception("fail")), \
         patch("sys.exit", side_effect=SystemExit(1)):
        from tsn_case_gen_.cli import main
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1