import pytest
from tsn_case_gen_.domain.route_generator import RouteGenerator


# --- Fixtures ---
@pytest.fixture
def simple_topo_rg():
    """Provides a simple topology for route generation tests."""
    return {
        "topology": {
            "delay_units": "MICRO_SECOND",
            "default_bandwidth_mbps": 1000,
            "switches": [
                {"id": "SW0", "ports": 8, "domain": 0},
                {"id": "SW1", "ports": 8, "domain": 0}
            ],
            "end_systems": [
                {"id": "ES0", "domain": 0},
                {"id": "ES1", "domain": 0},
                {"id": "ES_ISO", "domain": 0}
            ],
            "links": [
                {"id": "L0", "source": "ES0", "destination": "SW0", "sourcePort": 0, "destinationPort": 0, "domain": 0},
                {"id": "L1", "source": "SW0", "destination": "ES0", "sourcePort": 0, "destinationPort": 0, "domain": 0},
                {"id": "L2", "source": "SW0", "destination": "SW1", "sourcePort": 1, "destinationPort": 0, "domain": 0},
                {"id": "L3", "source": "SW1", "destination": "SW0", "sourcePort": 0, "destinationPort": 1, "domain": 0},
                {"id": "L4", "source": "SW1", "destination": "ES1", "sourcePort": 1, "destinationPort": 0, "domain": 0},
                {"id": "L5", "source": "ES1", "destination": "SW1", "sourcePort": 0, "destinationPort": 1, "domain": 0},
                {"id": "L6", "source": "SW0", "destination": "SW1", "sourcePort": 2, "destinationPort": 2, "domain": 0},
                {"id": "L7", "source": "SW1", "destination": "SW0", "sourcePort": 2, "destinationPort": 2, "domain": 0},
                {"id": "L8", "source": "SW1", "destination": "ES_ISO", "sourcePort": 3, "destinationPort": 0, "domain": 0},
                {"id": "L9", "source": "ES_ISO", "destination": "SW1", "sourcePort": 0, "destinationPort": 3, "domain": 0},
            ]
        }
    }

MIN_STREAMS_RG = {"delay_units": "MICRO_SECOND", "streams": []}
MIN_TRAFFIC_TYPES_RG = []

# --- Test _build_graph ---

def test_build_graph_nodes_and_edges(simple_topo_rg):
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="")
    graph = gen.graph
    assert "ES0" in graph.nodes
    assert "SW0" in graph.nodes
    assert "ES_ISO" in graph.nodes
    assert graph.nodes["ES0"]["type"] == "end_system"
    assert graph.nodes["SW0"]["type"] == "switch"
    assert graph.has_edge("ES0", "SW0")
    assert graph.has_edge("SW0", "SW1")
    assert not graph.has_edge("ES0", "ES1")
    assert 'bandwidth_mbps' in graph.get_edge_data("SW0", "SW1")


# --- Test _find_paths ---

def test_find_paths_single_shortest(simple_topo_rg):
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="", consider_link_utilization=False)
    paths = gen._find_paths("ES0", "ES1", num_paths=1)
    assert len(paths) == 1
    assert paths[0] == ["ES0", "SW0", "SW1", "ES1"]

def test_find_paths_redundant(simple_topo_rg):
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="", consider_link_utilization=False)
    paths = gen._find_paths("ES0", "ES1", num_paths=2)
    assert len(paths) >= 1
    assert paths[0] == ["ES0", "SW0", "SW1", "ES1"]
    if len(paths) > 1:
         assert paths[1] != paths[0]
         
def test_find_paths_fewer_than_requested(simple_topo_rg):
    gen = RouteGenerator(
        topology=simple_topo_rg["topology"],
        streams=MIN_STREAMS_RG,
        traffic_types=MIN_TRAFFIC_TYPES_RG,
        traffic_type="",
        consider_link_utilization=False
    )
    paths = gen._find_paths("ES0", "ES1", num_paths=5)
    assert len(paths) <= 5
    assert all(path[0] == "ES0" and path[-1] == "ES1" for path in paths)


def test_find_paths_no_path_exists(simple_topo_rg):
    # Remove links to ES_ISO to simulate no path
    topo = simple_topo_rg["topology"].copy()
    topo["links"] = [link for link in topo["links"] if "ES_ISO" not in (link["source"], link["destination"])]
    gen = RouteGenerator(topology=topo, streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="")
    paths = gen._find_paths("ES0", "ES_ISO", num_paths=1)
    assert paths == []

def test_find_paths_no_redundant_path(simple_topo_rg):
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="", consider_link_utilization=False)
    paths = gen._find_paths("ES0", "ES1", num_paths=2)
    assert len(paths) == 1
    assert paths[0] == ["ES0", "SW0", "SW1", "ES1"]

def test_find_paths_no_path_between_end_systems(simple_topo_rg):
    # Remove links to ES_ISO to simulate no path
    topo = simple_topo_rg["topology"].copy()
    topo["links"] = [link for link in topo["links"] if "ES_ISO" not in (link["source"], link["destination"])]
    gen = RouteGenerator(topology=topo, streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="")
    paths = gen._find_paths("ES0", "ES_ISO", num_paths=1)
    assert paths == []

# --- Test _calcutate_min_e2e_delay

def test_calculate_min_e2e_delay(mocker):
    mocker.patch('tsn_case_gen_.domain.route_generator.get_delays_from_traffic_type', return_value=(100, 500))
    mocker.patch('numpy.random.lognormal', return_value=250.0)

    gen = RouteGenerator(topology={}, streams=MIN_STREAMS_RG, traffic_types=[{"name": "ISOCHRONOUS", "min_delay": 100, "max_delay": 500}], traffic_type="ISOCHRONOUS")
    path = ["ES0", "SW0", "SW1", "ES1"]
    traffic = "ISOCHRONOUS"

    expected_delay = 750.0
    delay = gen._calculate_min_e2e_delay(path, traffic)
    assert delay == pytest.approx(expected_delay)

def test_calculate_min_e2e_delay_best_effort(mocker):
    mocker.patch('route_generator.get_delays_from_traffic_type', return_value=(None, None))
    gen = RouteGenerator(topology={}, streams=MIN_STREAMS_RG, traffic_types=[], traffic_type="")
    path = ["ES0", "SW0", "SW1", "ES1"]
    traffic = "BEST-EFFORT"
    delay = gen._calculate_min_e2e_delay(path, traffic)
    assert delay == 0.0

def test_min_e2e_delay_multiple_hops(mocker):
    mocker.patch('tsn_case_gen_.domain.route_generator.get_delays_from_traffic_type', return_value=(100, 500))
    mocker.patch('numpy.random.lognormal', return_value=250.0)

    gen = RouteGenerator(topology={}, streams=MIN_STREAMS_RG, traffic_types=[{"name": "ISOCHRONOUS", "min_delay": 100, "max_delay": 500}], traffic_type="ISOCHRONOUS")
    path = ["ES0", "SW0", "SW1", "ES1"]
    traffic_type = "ISOCHRONOUS"

    expected_delay = 750.0
    delay = gen._calculate_min_e2e_delay(path, traffic_type)
    assert delay == pytest.approx(expected_delay)

# --- Test _find link ---

def test_find_link_exists(simple_topo_rg):
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="")
    link = gen._find_link("SW0", "SW1")
    assert link is not None
    assert link["id"] in ["L2", "L6"]

def test_find_link_does_not_exist(simple_topo_rg):
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="")
    link = gen._find_link("ES0", "ES1")
    assert link is None


# --- Testing for empty topology ---

def test_empty_topology():
    empty_topo = {
        "topology": {
            "delay_units": "MICRO_SECOND",
            "default_bandwidth_mbps": 1000,
            "switches": [],
            "end_systems": [],
            "links": []
        }
    }
    gen = RouteGenerator(topology=empty_topo["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="")
    graph = gen.graph
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0

# --- Testing for no end systems ---
def test_no_end_systems(simple_topo_rg):
    no_end_system_topo = {
        "topology": {
            "delay_units": "MICRO_SECOND",
            "default_bandwidth_mbps": 1000,
            "switches": [{"id": "SW0", "ports": 8, "domain": 0}],
            "end_systems": [],
            "links": [{"id": "L0", "source": "SW0", "destination": "SW0", "sourcePort": 0, "destinationPort": 0, "domain": 0}]
        }
    }
    gen = RouteGenerator(topology=no_end_system_topo["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="")
    assert "ES0" not in gen.graph.nodes
    assert "SW0" in gen.graph.nodes


# --- Test _update_link_utilization

def test_update_link_utilization(simple_topo_rg):
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="", consider_link_utilization=True)
    
    stream = {
        "id": "stream1",
        "source": "ES0",
        "destinations": ["ES1"],
        "size": 1000,
        "period": 1000000,
    }
    paths = [["ES0", "SW0", "SW1", "ES1"]]
    
    gen._update_link_utilization(paths, stream)
    
    edge_data = gen.graph.get_edge_data("SW0", "SW1")
    assert "utilization" in edge_data
    assert edge_data["utilization"] > 0

# --- Testing for BEST-EFFORT traffic type ---

def test_best_effort_traffic_type(simple_topo_rg):
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=MIN_STREAMS_RG, traffic_types=MIN_TRAFFIC_TYPES_RG, traffic_type="BEST-EFFORT")
    path = ["ES0", "SW0", "SW1", "ES1"]
    delay = gen._calculate_min_e2e_delay(path, "BEST-EFFORT")
    assert delay == 0.0

def test_generate_route_for_stream_valid(mocker, simple_topo_rg):
    # Patch delay calculation for deterministic output
    mocker.patch('tsn_case_gen_.domain.route_generator.RouteGenerator._calculate_min_e2e_delay', return_value=123.0)
    streams = {
        "delay_units": "MICRO_SECOND",
        "streams": [
            {
                "id": 1,
                "source": "ES0",
                "destinations": [
                    {
                        "id": "ES1",
                        "deadline": 1000
                    }
                ],
                "type": "ISOCHRONOUS"
            }
        ]
    }

    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=streams, traffic_types=[{"name": "ISOCHRONOUS", "min_delay": 100, "max_delay": 500}], traffic_type="ISOCHRONOUS")
    route = gen._generate_route_for_stream(streams["streams"][0])
    assert route is not None
    assert route["flow_id"] == 1
    assert route["min_e2e_delay"] == 123.0
    assert len(route["paths"]) == 1
    assert route["paths"][0][0]["node"] == "ES0"
    assert route["paths"][0][-1]["node"] == "ES1"

def test_generate_route_for_stream_source_missing(mocker, simple_topo_rg):
    streams = {
        "delay_units": "MICRO_SECOND",
        "streams": [
            {
                "id": 2,
                "source": "MISSING",
                "destinations": ["ES1"],
                "type": "ISOCHRONOUS"
            }
        ]
    }
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=streams, traffic_types=[], traffic_type="ISOCHRONOUS")
    route = gen._generate_route_for_stream(streams["streams"][0])
    assert route is None

def test_generate_route_for_stream_destination_missing(mocker, simple_topo_rg):
    streams = {
        "delay_units": "MICRO_SECOND",
        "streams": [
            {
                "id": 3,
                "source": "ES0",
                "destinations": [
                    {
                        "id": "MISSING",
                        "deadline": None
                    }
                ],
                "type": "ISOCHRONOUS"
            }
        ]
    }
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=streams, traffic_types=[], traffic_type="ISOCHRONOUS")
    route = gen._generate_route_for_stream(streams["streams"][0])
    assert route is None

def test_generate_route_for_stream_no_path(mocker, simple_topo_rg):
    # Remove all links to break connectivity
    broken_topo = simple_topo_rg["topology"].copy()
    broken_topo["links"] = []
    streams = {
        "delay_units": "MICRO_SECOND",
        "streams": [
            {
                "id": 4,
                "source": "ES0",
                "destinations": [
                    {
                        "id": "ES1",
                        "deadline": None
                    }
                ],
                "type": "ISOCHRONOUS"
            }
        ]
    }
    gen = RouteGenerator(topology=broken_topo, streams=streams, traffic_types=[], traffic_type="ISOCHRONOUS")
    route = gen._generate_route_for_stream(streams["streams"][0])
    assert route is None


def test_generate_route_for_stream_multicast(mocker, simple_topo_rg):
    # Patch delay calculation for deterministic output
    mocker.patch('tsn_case_gen_.domain.route_generator.RouteGenerator._calculate_min_e2e_delay', return_value=42.0)
    streams = {
        "delay_units": "MICRO_SECOND",
        "streams": [
            {
                "id": 5,
                "source": "ES0",
                "destinations": [
                    {"id": "ES1", "deadline": None},
                    {"id": "ES_ISO", "deadline": None}
                ],
                "type": "ISOCHRONOUS"
            }
        ]
    }
    gen = RouteGenerator(topology=simple_topo_rg["topology"], streams=streams, traffic_types=[{"name": "ISOCHRONOUS", "min_delay": 100, "max_delay": 500}], traffic_type="ISOCHRONOUS")
    route = gen._generate_route_for_stream(streams["streams"][0])
    assert route is not None
    assert route["flow_id"] == 5
    assert route["min_e2e_delay"] == 42.0
    assert len(route["paths"]) == 2
    dest_nodes = {p[-1]["node"] for p in route["paths"]}
    assert {"ES1", "ES_ISO"} == dest_nodes
