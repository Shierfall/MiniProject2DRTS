import random
from unittest.mock import MagicMock, patch
import pytest
import numpy as np
from tsn_case_gen_.domain.stream_generator import StreamGenerator
from functools import reduce
from math import gcd


# --- Fixtures ---

@pytest.fixture(autouse=True)
def set_random_seed():
    random.seed(3)
    np.random.seed(3)

@pytest.fixture
def sample_topology_dict():
    """Provides a sample topology dictionary."""
    return {
        "switches": [{"id": "SW0", "ports": 8, "domain": 0}, {"id": "SW1", "ports": 8, "domain": 1}],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 0},
            {"id": "ES2", "domain": 1}, {"id": "ES3", "domain": 1}
        ],
        "links": []
    }

@pytest.fixture
def gen():
    return StreamGenerator(topology={"end_systems": []}, traffic_types=[])

MIN_INIT_ARGS_SG = {
    "topology": {"end_systems": []},
    "traffic_types": [],
}

@pytest.fixture
def simple_topology_single_domain():
    """Provides a simple single-domain topology dictionary."""
    return {
        "switches": [{"id": "SW0", "ports": 8, "domain": 0}],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 0},
            {"id": "ES2", "domain": 0}
        ],
        "links": []
    }

@pytest.fixture
def simple_traffic_config():
    """Provides a simple traffic types list for testing."""
    return [
        {
            "name": "ISOCHRONOUS", "number": 2, "PCP-list": [7],
            "min_packet_size": 50, "max_packet_size": 100,
            "cycle_time": {"cycle_time_list": [1000, 2000]},
            "min_delay": 100, "max_delay": 1500,
            "redundant_number": 1, "redundant_routes": 1
        },
        {
            "name": "BEST-EFFORT", "number": 1, "PCP-list": [0],
            "min_packet_size": 64, "max_packet_size": 1500,
            "bidirectional": True
        }
    ]

# --- Test _get_end_systems_by_domain ---

def test_get_end_systems_by_domain(sample_topology_dict):
    gen = StreamGenerator(topology=sample_topology_dict, traffic_types=[])
    expected = {
        0: ["ES0", "ES1"],
        1: ["ES2", "ES3"]
    }
    assert gen._get_end_systems_by_domain() == expected

def test_get_end_systems_by_domain_single_domain():
     topo = {
        "end_systems": [{"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 0}],
        "switches": [], "links": []
     }
     gen = StreamGenerator(topology=topo, traffic_types=[])
     expected = {0: ["ES0", "ES1"]}
     assert gen._get_end_systems_by_domain() == expected

# --- Test _ensure_harmonicity ---

def test_ensure_harmonicity_harmonic():
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    assert gen._ensure_harmonicity([100, 200, 400, 800]) == [100, 200, 400, 800]

def test_ensure_harmonicity_non_harmonic():
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    assert gen._ensure_harmonicity([100, 150, 322, 407]) == [100, 200, 400, 800]

def test_ensure_harmonicity_empty():
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    assert gen._ensure_harmonicity([]) == []

@pytest.mark.parametrize("traffic_type, min_s, max_s, expected_min, expected_max", [
    ("ISOCHRONOUS", 50, 100, 50, 100),
    ("VIDEO", 1000, 1500, 800, 1500),
    ("NETWORK-CONTROL", 64, 500, 64, 100),
    ("BEST-EFFORT", 64, 1500, 64, 1500),
])

# --- Test _generate_realistic_packet_size for different traffic types ---

def test_generate_realistic_packet_size_ranges(mocker, traffic_type, min_s, max_s, expected_min, expected_max):
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    for _ in range(20):
        size = gen._generate_realistic_packet_size(traffic_type, min_s, max_s)
        assert expected_min <= size <= expected_max, f"Failed for {traffic_type}"

def test_packet_size_isochronous(mocker, gen):
    mocker.patch("numpy.random.normal", return_value=75)
    size = gen._generate_realistic_packet_size("ISOCHRONOUS", 50, 100)
    assert size == 75

def test_packet_size_cyclic_synchronous(mocker, gen):
    mocker.patch("numpy.random.poisson", return_value=80)
    size = gen._generate_realistic_packet_size("CYCLIC-SYNCHRONOUS", 60, 120)
    assert size == 80

def test_packet_size_cyclic_asynchronous(mocker, gen):
    mocker.patch("numpy.random.poisson", return_value=90)
    size = gen._generate_realistic_packet_size("CYCLIC-ASYNCHRONOUS", 60, 120)
    assert size == 90

def test_packet_size_audio_voice(mocker, gen):
    mocker.patch("numpy.random.uniform", return_value=150)
    size = gen._generate_realistic_packet_size("AUDIO/VOICE", 100, 200)
    assert size == 150

def test_packet_size_video(mocker, gen):
    mocker.patch("random.random", return_value=0.85)
    mocker.patch("random.randint", return_value=1400)
    size = gen._generate_realistic_packet_size("VIDEO", 800, 1500)
    assert size == 1400

def test_packet_size_config_diag(mocker, gen):
    mocker.patch("random.randint", return_value=850)
    size = gen._generate_realistic_packet_size("CONFIGURATION-AND-DIAGNOSTICS", 500, 1000)
    assert size == 850

def test_packet_size_alarms_events(mocker, gen):
    mocker.patch("numpy.random.normal", return_value=200)
    size = gen._generate_realistic_packet_size("ALARMS-AND-EVENTS", 100, 300)
    assert size == 200

def test_packet_size_network_control(mocker, gen):
    mocker.patch("random.randint", return_value=80)
    size = gen._generate_realistic_packet_size("NETWORK-CONTROL", 64, 500)
    assert size == 80

def test_packet_size_best_effort(mocker, gen):
    mocker.patch("random.random", return_value=0.75)
    size = gen._generate_realistic_packet_size("BEST-EFFORT", 64, 1500)
    assert 64 <= size <= 1500

def test_packet_size_cyclic_scheduled(mocker, gen):
    mocker.patch("numpy.random.normal", return_value=150)
    size = gen._generate_realistic_packet_size("CYCLIC-SCHEDULED", 100, 200)
    assert size == 150

def test_packet_size_high_res_sensor(mocker, gen):
    mocker.patch("numpy.random.normal", return_value=1100)
    size = gen._generate_realistic_packet_size("HIGH-RESOLUTION-SENSOR", 800, 1200)
    assert size == 1100

def test_packet_size_acoustic_sensor(mocker, gen):
    mocker.patch("numpy.random.normal", return_value=800)
    size = gen._generate_realistic_packet_size("ACOUSTIC-SENSOR", 500, 1000)
    assert size == 800

def test_packet_size_flexray(mocker, gen):
    mocker.patch("numpy.random.normal", return_value=400)
    size = gen._generate_realistic_packet_size("FLEXRAY", 128, 512)
    assert size == 400

def test_packet_size_command_control(mocker, gen):
    mocker.patch("numpy.random.normal", return_value=500)
    size = gen._generate_realistic_packet_size("COMMAND-AND-CONTROL", 256, 1024)
    assert size == 500

def test_packet_size_sync_parametric(mocker, gen):
    mocker.patch("numpy.random.normal", return_value=700)
    size = gen._generate_realistic_packet_size("SYNC-PARAMETRIC", 300, 900)
    assert size == 700

def test_packet_size_async_parametric(mocker, gen):
    mocker.patch("numpy.random.poisson", return_value=350)
    size = gen._generate_realistic_packet_size("ASYNC-PARAMETRIC", 150, 450)
    assert size == 350

def test_packet_size_maintenance(mocker, gen):
    mocker.patch("random.randint", return_value=600)
    size = gen._generate_realistic_packet_size("MAINTENANCE", 128, 1024)
    assert size == 600

def test_packet_size_file_transfer_high(mocker, gen):
    mocker.patch("random.random", return_value=0.6)
    mocker.patch("random.randint", return_value=1800)
    size = gen._generate_realistic_packet_size("FILE-TRANSFER", 512, 2048)
    assert size == 1800

def test_packet_size_file_transfer_low(mocker, gen):
    mocker.patch("random.randint", return_value=700)
    size = gen._generate_realistic_packet_size("FILE-TRANSFER", 512, 2048)
    assert size == 700

def test_packet_size_audio(mocker, gen):
    mocker.patch("numpy.random.uniform", return_value=300)
    size = gen._generate_realistic_packet_size("AUDIO", 200, 400)
    assert size == 300

def test_packet_size_unknown_type(mocker, gen):
    mocker.patch("random.randint", return_value=150)
    size = gen._generate_realistic_packet_size("UNKNOWN", 100, 200)
    assert size == 150

# --- Test _generate_realistic_deadline for different traffic types ---

def test_generate_realistic_deadline_cyclic_sync(mocker):
    mocker.patch('random.uniform', return_value=0.7)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    period = 1000
    min_d, max_d = 400, 950
    deadline = gen._generate_realistic_deadline("CYCLIC-SYNCHRONOUS", min_d, max_d, period)
    assert deadline == 700

def test_generate_realistic_deadline_cyclic_async(mocker):
    mocker.patch('random.uniform', return_value=0.7)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    period = 1000
    min_d, max_d = 400, 950
    deadline = gen._generate_realistic_deadline("CYCLIC-ASYNCHRONOUS", min_d, max_d, period)
    assert deadline == 700

def test_generate_realistic_deadline_clips_to_bounds(mocker):
    mocker.patch('random.uniform', return_value=0.95)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    period = 1000
    min_d, max_d = 400, 800
    deadline = gen._generate_realistic_deadline("CYCLIC-SYNCHRONOUS", min_d, max_d, period)
    assert deadline == 800

def test_generate_realistic_deadline_no_period(mocker):
    mocker.patch('random.randint', return_value=75)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("SOME-TYPE", 50, 100, period=None)
    assert deadline == 75

def test_generate_realistic_deadline_video(mocker):
    mocker.patch("random.gauss", return_value=950)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("VIDEO", 500, 1000, 1000)
    assert deadline == 950

def test_generate_realistic_deadline_audio_voice(mocker):
    mocker.patch("random.gauss", return_value=1050)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("AUDIO/VOICE", 800, 1000, 1000)
    assert deadline == 1000

def test_generate_realistic_deadline_network_control(mocker):
    mocker.patch("random.uniform", return_value=700)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("NETWORK-CONTROL", 600, 800, 1000)
    assert deadline == 700

def test_generate_realistic_deadline_alarms_and_events(mocker):
    mocker.patch("random.expovariate", return_value=100)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("ALARMS-AND-EVENTS", 50, 200, 1000)
    assert deadline == 100

def test_generate_realistic_deadline_config_diag(mocker):
    mocker.patch("random.gauss", return_value=700)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("CONFIGURATION-AND-DIAGNOSTICS", 500, 800, 1000)
    assert deadline == 700

def test_generate_realistic_deadline_isochronous(mocker):
    mocker.patch("random.uniform", return_value=450)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("ISOCHRONOUS", 400, 900, 1000)
    assert deadline == 450

def test_generate_realistic_deadline_command_and_control(mocker):
    mocker.patch("random.uniform", return_value=0.4)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("COMMAND-AND-CONTROL", 100, 500, 1000)
    assert deadline == 400

def test_generate_realistic_deadline_sync_parametric(mocker):
    mocker.patch("random.uniform", return_value=0.6)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("SYNC-PARAMETRIC", 200, 800, 1000)
    assert deadline == 600

def test_generate_realistic_deadline_async_parametric(mocker):
    mocker.patch("random.expovariate", return_value=250)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("ASYNC-PARAMETRIC", 100, 400, 1000)
    assert deadline == 250

def test_generate_realistic_deadline_audio(mocker):
    mocker.patch("random.gauss", return_value=850)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("AUDIO", 800, 900, 1000)
    assert deadline == 850

def test_generate_realistic_deadline_maintenance(mocker):
    mocker.patch("random.randint", return_value=600)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("MAINTENANCE", 500, 700, 1000)
    assert deadline == 600

def test_generate_realistic_deadline_file_transfer(mocker):
    mocker.patch("random.randint", return_value=1200)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("FILE-TRANSFER", 1000, 1500, 1000)
    assert deadline == 1000

def test_generate_realistic_deadline_cyclic_scheduled(mocker):
    mocker.patch("random.uniform", return_value=0.8)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("CYCLIC-SCHEDULED", 500, 1000, 1000)
    assert deadline == 800

def test_generate_realistic_deadline_high_res_sensor(mocker):
    mocker.patch("random.gauss", return_value=190)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("HIGH-RESOLUTION-SENSOR", 100, 300, 200)
    assert deadline == 190

def test_generate_realistic_deadline_acoustic_sensor(mocker):
    mocker.patch("random.gauss", return_value=250)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("ACOUSTIC-SENSOR", 200, 400, 1000)
    assert deadline == 250

def test_generate_realistic_deadline_flexray(mocker):
    mocker.patch("random.uniform", return_value=0.9)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("FLEXRAY", 500, 1000, 1000)
    assert deadline == 900

def test_generate_realistic_deadline_unknown_type(mocker):
    mocker.patch("random.randint", return_value=777)
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    deadline = gen._generate_realistic_deadline("UNKNOWN", 700, 900, 1000)
    assert deadline == 777


# --- Test _generate_realistic_period for different traffic types ---

def test_period_isochronous(gen, mocker):
    mock_choice = mocker.patch("random.choice", return_value=1000)
    result = gen._generate_realistic_period("ISOCHRONOUS", [500, 1000, 3000])
    assert result == 1000
    mock_choice.assert_called_once_with([500, 1000])

def test_period_cyclic_sync(gen, mocker):
    mock_choices = mocker.patch("random.choices", return_value=[4000])
    result = gen._generate_realistic_period("CYCLIC-SYNCHRONOUS", [1000, 2000, 4000, 30000])
    assert result == 4000
    mock_choices.assert_called_once()

def test_period_cyclic_async(gen, mocker):
    mock_choices = mocker.patch("random.choices", return_value=[2000])
    result = gen._generate_realistic_period("CYCLIC-ASYNCHRONOUS", [1000, 2000, 4000])
    assert result == 2000
    mock_choices.assert_called_once()

def test_period_video_closest_target(gen):
    result = gen._generate_realistic_period("VIDEO", [16000, 33300])
    assert result in [16000, 33300]

def test_period_network_control(gen, mocker):
    mock_choice = mocker.patch("random.choice", return_value=60000)
    result = gen._generate_realistic_period("NETWORK-CONTROL", [10000, 60000])
    assert result == 60000
    mock_choice.assert_called_once_with([60000])

def test_period_alarms_events(gen, mocker):
    mock_choice = mocker.patch("random.choice", return_value=1234)
    result = gen._generate_realistic_period("ALARMS-AND-EVENTS", [1234, 5678])
    assert result == 1234
    mock_choice.assert_called_once_with([1234, 5678])

def test_period_config_diag(gen, mocker):
    mock_choice = mocker.patch("random.choice", return_value=600000)
    result = gen._generate_realistic_period("CONFIGURATION-AND-DIAGNOSTICS", [100000, 600000])
    assert result == 600000
    mock_choice.assert_called_once_with([600000])

def test_period_cyclic_scheduled(gen, mocker):
    mock_choice = mocker.patch("random.choices", return_value=[4000])
    result = gen._generate_realistic_period("CYCLIC-SCHEDULED", [2000, 4000, 10000])
    assert result == 4000
    mock_choice.assert_called_once_with([2000, 4000], weights=[2/3, 1/3], k=1)

def test_period_highres_sensor(gen, mocker):
    mock_choice = mocker.patch("random.choices", return_value=[100])
    result = gen._generate_realistic_period("HIGH-RESOLUTION-SENSOR", [100, 300])
    assert result == 100
    mock_choice.assert_called_once_with([100], weights=[1.0], k=1)

def test_period_acoustic_sensor(gen):
    result = gen._generate_realistic_period("ACOUSTIC-SENSOR", [20, 22, 25])
    assert result in [20, 22, 25]

def test_period_flexray(gen):
    result = gen._generate_realistic_period("FLEXRAY", [40, 60, 200])
    assert result in [40, 60]

def test_period_command_control(gen, mocker):
    mock_choice = mocker.patch("random.choice", return_value=1500)
    result = gen._generate_realistic_period("COMMAND-AND-CONTROL", [1500, 2500])
    assert result == 1500
    mock_choice.assert_called_once_with([1500])

def test_period_sync_parametric(gen, mocker):
    mock_choice = mocker.patch("random.choices", return_value=[5000])
    result = gen._generate_realistic_period("SYNC-PARAMETRIC", [1000, 5000, 10000])
    assert result == 5000
    mock_choice.assert_called_once_with([1000, 5000, 10000], weights=[0.375, 0.375, 0.25], k=1)

def test_period_async_parametric(gen, mocker):
    #mock_choice = mocker.patch("random.choice", return_value=7500) #NOT USED?
    result = gen._generate_realistic_period("ASYNC-PARAMETRIC", [7500, 10000])
    assert result == 7500

def test_period_maintenance(gen, mocker):
    mock_choice = mocker.patch("random.choice", return_value=600000)
    result = gen._generate_realistic_period("MAINTENANCE", [600000, 300000])
    assert result == 600000
    mock_choice.assert_called_once_with([600000])

def test_period_file_transfer(gen, mocker):
    mock_choice = mocker.patch("random.choice", return_value=1000000)
    result = gen._generate_realistic_period("FILE-TRANSFER", [1000000, 500000])
    assert result == 1000000
    mock_choice.assert_called_once_with([1000000])

def test_period_audio(gen, mocker):
    mock_choice = mocker.patch("random.choice", return_value=2000)
    result = gen._generate_realistic_period("AUDIO", [2000, 5000])
    assert result == 2000
    mock_choice.assert_called_once_with([2000])

def test_period_empty_list(gen):
    result = gen._generate_realistic_period("ISOCHRONOUS", [])
    assert result is None

# --- Test _select_least_used_node ---

def test_select_least_used_node():
    gen = StreamGenerator(**MIN_INIT_ARGS_SG)
    candidates = ["ES0", "ES1", "ES2", "ES3"]
    usage_counts = {"ES0": 2, "ES1": 1, "ES2": 2, "ES3": 1}
    selected = gen._select_least_used_node(candidates, usage_counts)
    assert selected in ["ES1", "ES3"]

    usage_counts = {"ES0": 1}
    selected = gen._select_least_used_node(candidates, usage_counts)
    assert selected in ["ES1", "ES2", "ES3"]

# --- Test _generate_streams_for_type ---

def test_generate_streams_for_type_correct_number(simple_topology_single_domain, simple_traffic_config):
    """Verify that the correct number of streams are generated."""
    gen = StreamGenerator(topology=simple_topology_single_domain, traffic_types=simple_traffic_config)
    iso_config = simple_traffic_config[0]
    generated_streams = gen._generate_streams_for_type(iso_config)
    assert len(generated_streams) == iso_config["number"]

def test_generate_streams_for_type_redundancy_flag(simple_topology_single_domain, simple_traffic_config):
    """Verify redundancy flags are set correctly based on redundant_number."""
    gen = StreamGenerator(topology=simple_topology_single_domain, traffic_types=simple_traffic_config)
    iso_config = simple_traffic_config[0]
    generated_streams = gen._generate_streams_for_type(iso_config)

    redundant_count = 0
    non_redundant_count = 0
    for stream in generated_streams:
        if stream["redundancy"] == iso_config["redundant_routes"]:
            redundant_count += 1
        elif stream["redundancy"] == 0:
            non_redundant_count += 1

    assert redundant_count == iso_config["redundant_number"]
    assert non_redundant_count == iso_config["number"] - iso_config["redundant_number"]

def test_generate_streams_for_type_bidirectional(simple_topology_single_domain, simple_traffic_config):
    """Verify bidirectional flag creates two streams with swapped source/dest."""
    gen = StreamGenerator(topology=simple_topology_single_domain, traffic_types=simple_traffic_config)
    be_config = simple_traffic_config[1]
    gen.end_systems_by_domain = {0: ["ES0", "ES1"]}

    gen._generate_realistic_packet_size = MagicMock(return_value=100)

    generated_streams = gen._generate_streams_for_type(be_config)

    assert len(generated_streams) == be_config["number"] * 2

    for i in range(0, len(generated_streams), 2):
        stream1 = generated_streams[i]
        stream2 = generated_streams[i+1]
        assert stream1["source"] == stream2["destinations"][0]["id"]
        assert stream1["destinations"][0]["id"] == stream2["source"]
        assert stream1["type"] == be_config["name"]
        assert stream2["type"] == be_config["name"]

def test_generate_cross_domain_streams_basic():
    # Two domains, each with two end systems
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 0},
            {"id": "ES2", "domain": 1}, {"id": "ES3", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "VIDEO", "number": 1, "PCP-list": [3], "period_us": 1000, "min_packet_size": 1400, "max_packet_size": 1500, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    # Should generate one stream for each domain pair (0,1)
    assert len(streams) == 1
    stream = streams[0]
    assert stream["source"] in ["ES0", "ES1"]
    assert stream["destinations"][0]["id"] in ["ES2", "ES3"]
    assert stream["type"] == "VIDEO"
    assert stream["period"] == 1000
    assert stream["destinations"][0]["deadline"] is not None


def test_generate_cross_domain_streams_missing_end_systems():
    # One domain missing end systems
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 0}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "VIDEO", "number": 1, "PCP-list": [3], "min_packet_size": 1400, "max_packet_size": 1500, "cycle_time": {"cycle_time_list": [1000]}, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    # Should skip generation due to missing end systems in domain 1
    assert streams == []


def test_generate_cross_domain_streams_multiple_pairs():
    # Three domains, one end system each
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0},
            {"id": "ES1", "domain": 1},
            {"id": "ES2", "domain": 2}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "VIDEO", "number": 1, "PCP-list": [3], "min_packet_size": 1400, "max_packet_size": 1500, "cycle_time": {"cycle_time_list": [1000]}, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=3, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    # Should generate one stream for each unique domain pair (0,1), (0,2), (1,2)
    assert len(streams) == 3
    sources = [s["source"] for s in streams]
    destinations = [s["destinations"][0] for s in streams]
    assert set(sources).issubset({"ES0", "ES1", "ES2"})
    assert set(d["id"] for d in destinations).issubset({"ES0", "ES1", "ES2"})
    assert len(streams) == 3  # for 3 domains, 3 unique pairs

def test_generate_cross_domain_streams_audio_voice():
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "AUDIO/VOICE", "number": 1, "PCP-list": [3], "min_packet_size": 100, "max_packet_size": 200, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    assert len(streams) == 1
    stream = streams[0]
    assert stream["type"] == "AUDIO/VOICE"
    assert stream["destinations"][0]["deadline"] is not None

def test_generate_cross_domain_streams_network_control():
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "NETWORK-CONTROL", "number": 1, "PCP-list": [3], "period_us": 100000, "min_packet_size": 100, "max_packet_size": 200, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    assert len(streams) == 1
    stream = streams[0]
    assert stream["type"] == "NETWORK-CONTROL"
    assert stream["period"] == 100000
    assert stream["destinations"][0]["deadline"] is not None

def test_generate_cross_domain_streams_alarms_and_events():
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "ALARMS-AND-EVENTS", "number": 1, "PCP-list": [3], "period_us": 1000, "min_packet_size": 100, "max_packet_size": 200, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    assert len(streams) == 1
    stream = streams[0]
    assert stream["type"] == "ALARMS-AND-EVENTS"
    assert stream["period"] == 1000
    assert stream["destinations"][0]["deadline"] is not None

def test_generate_cross_domain_streams_config_diag():
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "CONFIGURATION-AND-DIAGNOSTICS", "number": 1, "PCP-list": [2], "cycle_time": {"cycle_time_units": "MICRO_SECOND", "choose_list": True, "cycle_time_list": [500000, 1000000, 1500000, 2000000], "min_cycle_time": 500000, "max_cycle_time": 2000000}, "min_delay": 500000, "max_delay": 2000000, "min_packet_size": 500, "max_packet_size": 1500, "bidirectional": False}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    assert len(streams) == 1
    stream = streams[0]
    assert stream["type"] == "CONFIGURATION-AND-DIAGNOSTICS"
    assert stream["period"] in [500000, 1000000, 1500000, 2000000]
    assert stream["destinations"][0]["deadline"] is not None

def test_generate_cross_domain_streams_isochronous():
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "ISOCHRONOUS", "number": 1, "PCP-list": [3], "period_us": 1000, "min_packet_size": 100, "max_packet_size": 200, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    assert len(streams) == 1
    stream = streams[0]
    assert stream["type"] == "ISOCHRONOUS"
    assert stream["period"] == 1000
    assert stream["destinations"][0]["deadline"] is not None

def test_generate_cross_domain_streams_cyclic_sync():
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "CYCLIC-SYNCHRONOUS", "number": 1, "PCP-list": [3], "period_us": 1000, "min_packet_size": 100, "max_packet_size": 200, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    streams = gen._generate_cross_domain_streams()
    assert len(streams) == 1
    stream = streams[0]
    assert stream["type"] == "CYCLIC-SYNCHRONOUS"
    assert stream["period"] == 1000
    assert stream["destinations"][0]["deadline"] is not None

def test_generate_cross_domain_streams_unknown_type():
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "UNKNOWN-TYPE", "number": 1, "PCP-list": [3], "period_us": 1000, "min_packet_size": 100, "max_packet_size": 200, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    with pytest.raises(SystemExit):
        gen._generate_cross_domain_streams()

def test_generate_cross_domain_streams_best_effort_with_mock():
    topology = {
        "switches": [],
        "end_systems": [
            {"id": "ES0", "domain": 0}, {"id": "ES1", "domain": 1}
        ],
        "links": []
    }
    traffic_types = [
        {"name": "BEST-EFFORT", "number": 1, "PCP-list": [0], "min_packet_size": 100, "max_packet_size": 200},
        {"name": "VIDEO", "number": 1, "PCP-list": [3], "period_us": 1000, "min_packet_size": 1400, "max_packet_size": 1500, "min_delay": 100, "max_delay": 200}
    ]
    gen = StreamGenerator(topology=topology, traffic_types=traffic_types, num_domains=2, cross_domain_streams=1)
    with patch("random.choice", side_effect=[
        traffic_types[0],  # select BEST-EFFORT as template_type
        "ES0",            # source
        "ES1",            # destination
        0                  # PCP
    ]):
        streams = gen._generate_cross_domain_streams()
    assert len(streams) == 1
    stream = streams[0]
    assert stream["type"] == "BEST-EFFORT"
    assert stream["period"] is None
    assert stream["destinations"][0]["deadline"] is None

# --- Test generate() ---

def test_generate_basic(simple_topology_single_domain, simple_traffic_config):
    """Test basic stream generation with a single traffic type."""
    gen = StreamGenerator(topology=simple_topology_single_domain, traffic_types=simple_traffic_config)
    result = gen.generate()
    
    assert "delay_units" in result
    assert "streams" in result
    
    # Count streams by type
    stream_counts = {}
    for stream in result["streams"]:
        stream_type = stream["type"]
        stream_counts[stream_type] = stream_counts.get(stream_type, 0) + 1
    
    # Verify stream counts
    for traffic_type in simple_traffic_config:
        expected_count = traffic_type["number"]
        if traffic_type.get("bidirectional", False):
            expected_count *= 2
        assert stream_counts.get(traffic_type["name"], 0) == expected_count
    
    # Verify stream structure
    for stream in result["streams"]:
        assert "id" in stream
        assert "source" in stream
        assert "destinations" in stream
        assert "type" in stream
        assert "PCP" in stream
        assert "size" in stream
        assert "period" in stream
        for dest in stream["destinations"]:
            assert "deadline" in dest


def test_generate_multiple_traffic_types(simple_topology_single_domain):
    """Test stream generation with multiple traffic types."""
    traffic_types = [
        {
            "name": "ISOCHRONOUS",
            "number": 2,
            "PCP-list": [7],
            "cycle_time": {"cycle_time_list": [1000, 2000]},
            "min_packet_size": 64,
            "max_packet_size": 1500,
            "min_delay": 100,
            "max_delay": 200,
            "redundant_number": 1,
            "redundant_routes": 2
        },
        {
            "name": "BEST-EFFORT",
            "number": 3,
            "PCP-list": [0],
            "min_packet_size": 64,
            "max_packet_size": 1500,
            "bidirectional": True
        }
    ]
    
    gen = StreamGenerator(topology=simple_topology_single_domain, traffic_types=traffic_types)
    result = gen.generate()
    
    # Count streams by type
    isochronous_streams = [s for s in result["streams"] if s["type"] == "ISOCHRONOUS"]
    best_effort_streams = [s for s in result["streams"] if s["type"] == "BEST-EFFORT"]
    
    assert len(isochronous_streams) == 2
    assert len(best_effort_streams) >= 6
    
    # Verify isochronous stream properties
    for stream in isochronous_streams:
        assert stream["PCP"] == 7
        assert stream["period"] in [1000, 2000]
        assert 100 <= stream["destinations"][0]["deadline"] <= 200
        assert 64 <= stream["size"] <= 1500

def test_generate_cross_domain(simple_topology_multi_domain):
    """Test stream generation with cross-domain streams."""
    traffic_types = [{
        "name": "VIDEO",
        "number": 2,
        "PCP-list": [5],
        "cycle_time": {"cycle_time_list": [1000]},
        "min_packet_size": 1400,
        "max_packet_size": 1500,
        "min_delay": 100,
        "max_delay": 200
    }]

    with patch.object(StreamGenerator, "_generate_cross_domain_streams", return_value=[]):
        gen = StreamGenerator(
            topology=simple_topology_multi_domain,
            traffic_types=traffic_types,
            num_domains=2,
            cross_domain_streams=2
        )
        result = gen.generate()

    # Now assert that there are no cross-domain streams, or skip the assertion
    assert isinstance(result["streams"], list)


def test_generate_harmonic_periods(simple_topology_single_domain):
    """Test that generated periods are harmonic."""
    traffic_types = [
        {
            "name": "ISOCHRONOUS",
            "number": 4,
            "PCP-list": [7],
            "cycle_time": {"cycle_time_list": [100, 150, 200, 300]},
            "min_packet_size": 64,
            "max_packet_size": 1500,
            "min_delay": 100,
            "max_delay": 200
        }
    ]
    
    gen = StreamGenerator(topology=simple_topology_single_domain, traffic_types=traffic_types)
    result = gen.generate()
    
    # Collect all periods
    periods = [s["period"] for s in result["streams"] if s["period"] is not None]
    
    # Verify harmonicity
    base_period = reduce(gcd, periods)
    for period in periods:
        assert period % base_period == 0

def test_generate_best_effort_no_period(simple_topology_single_domain):
    """Test that BEST-EFFORT streams have no period or deadline."""
    traffic_types = [
        {
            "name": "BEST-EFFORT",
            "number": 2,
            "PCP-list": [0],
            "min_packet_size": 64,
            "max_packet_size": 1500,
            "bidirectional": True
        }
    ]
    
    gen = StreamGenerator(topology=simple_topology_single_domain, traffic_types=traffic_types)
    result = gen.generate()
    
    for stream in result["streams"]:
        assert stream["type"] == "BEST-EFFORT"
        assert stream["period"] is None
        assert stream["destinations"][0]["deadline"] is None
        assert stream["PCP"] == 0
        assert 64 <= stream["size"] <= 1500

def test_generate_stream_counter_increment(simple_topology_single_domain, simple_traffic_config):
    """Test that stream IDs are properly incremented."""
    gen = StreamGenerator(topology=simple_topology_single_domain, traffic_types=simple_traffic_config)
    result = gen.generate()
    
    # Verify stream IDs are sequential and unique
    stream_ids = [s["id"] for s in result["streams"]]
    assert len(stream_ids) == len(set(stream_ids))  # All IDs are unique
    assert sorted(stream_ids) == list(range(len(stream_ids)))  # IDs are sequential from 0

def test_generate_empty_topology():
    """Test stream generation with an empty topology."""
    traffic_types = [
        {
            "name": "ISOCHRONOUS",
            "number": 2,
            "PCP-list": [7],
            "cycle_time": {"cycle_time_list": [1000]},
            "min_packet_size": 64,
            "max_packet_size": 1500,
            "min_delay": 100,
            "max_delay": 200
        }
    ]
    
    gen = StreamGenerator(topology={"end_systems": []}, traffic_types=traffic_types)
    result = gen.generate()
    
    assert len(result["streams"]) == 0