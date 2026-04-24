import pytest
import networkx as nx
from unittest.mock import patch, call, MagicMock
from tsn_case_gen_.domain.topology_generator import TopologyGenerator, logger

# Minimal init args 
MIN_INIT_ARGS = {
    "num_domains": 1,
    "topology_type": "mesh_graph",
    "num_switches": 4,
    "num_end_systems": 2,
    "end_systems_per_switch": [],
    "topology_params": "{'n': 2, 'm': 2}",
    "domain_connection_type": "line",
    "connections_per_domain_pair": 1,
    "delay_units": "MICRO_SECOND",
    "default_bandwidth_mbps": 1000,
}

# --- Fixtures ---
@pytest.fixture
def generator():

    gen = TopologyGenerator(**MIN_INIT_ARGS)

    gen.switch_counter = 0
    gen.node_counter = 0
    gen.link_counter = 0
    gen.used_ports = {}
    gen.domain_graphs = []
    return gen

# --- Test _parse_params ---

def test_parse_params_valid(generator):
    params_str = "{'n': 4, 'm': 3, 'flag': True}"
    expected = {'n': 4, 'm': 3, 'flag': True}
    assert generator._parse_params(params_str) == expected

def test_parse_params_invalid_syntax(generator):
    params_str = "{'n': 4 'm': 3}"
    with patch.object(logger, 'error') as mock_error:
        assert generator._parse_params(params_str) == {}
        mock_error.assert_called_once()

def test_parse_params_empty(generator):
    params_str = ""
    with patch.object(logger, 'error') as mock_error:
        assert generator._parse_params(params_str) == {}
        mock_error.assert_called_once()

# --- Test Graph Generation Helpers ---

def test_generate_mesh_graph_correct_size(generator):
    generator.num_switches = 6
    generator.topology_params = "{'n': 2, 'm': 3}"
    graph = generator._generate_mesh_graph()
    assert isinstance(graph, nx.Graph)
    assert len(graph.nodes) == 6
    assert graph.has_edge((0,0), (0,1))
    assert graph.has_edge((0,0), (1,0))

def test_generate_mesh_graph_missing_params(generator):
    generator.topology_params = "{'n': 2}"
    with patch.object(logger, 'error') as mock_error, \
         pytest.raises(SystemExit):
        generator._generate_mesh_graph()
    mock_error.assert_called_once()

def test_generate_mesh_graph_no_params_string(generator):
    generator.topology_params = ""
    with patch.object(logger, 'error') as mock_error, \
         pytest.raises(SystemExit):
        generator._generate_mesh_graph()
    mock_error.assert_called_once()


def test_generate_binomial_graph_correct_size(generator):
    generator.num_switches = 10
    generator.topology_params = "{'p': 0.5}"
    graph = generator._generate_binomial_graph()
    assert isinstance(graph, nx.Graph)
    assert len(graph.nodes) == 10

def test_generate_binomial_graph_missing_params(generator):
    generator.num_switches = 10
    generator.topology_params = "{}"
    with patch.object(logger, 'error') as mock_error, \
         pytest.raises(SystemExit):
        generator._generate_binomial_graph()
    mock_error.assert_called_once()

def test_generate_random_geometric_graph_correct_size(generator):
    generator.num_switches = 15
    generator.topology_params = "{'r': 0.3}"
    graph = generator._generate_random_geometric_graph()
    assert isinstance(graph, nx.Graph)
    assert len(graph.nodes) == 15

def test_generate_random_geometric_graph_missing_params(generator):
    generator.num_switches = 15
    generator.topology_params = "{}"
    with patch.object(logger, 'error') as mock_error, \
         pytest.raises(SystemExit):
        generator._generate_random_geometric_graph()
    mock_error.assert_called_once()

def test_generate_industrial_ring_single(generator):
    generator.num_switches = 5
    generator.topology_params = "{'cwsg_num_rings': 1}"
    graph = generator._generate_industrial_ring()
    assert isinstance(graph, nx.Graph)
    assert len(graph.nodes) == 5
    assert nx.is_connected(graph)
    assert graph.has_edge(0, 1)
    assert graph.has_edge(1, 2)
    assert graph.has_edge(2, 3)
    assert graph.has_edge(3, 4)
    assert graph.has_edge(4, 0) 

def test_generate_industrial_ring_multiple(generator):
    generator.num_switches = 9 
    generator.topology_params = "{'cwsg_num_rings': 3}"
    graph = generator._generate_industrial_ring()
    assert isinstance(graph, nx.Graph)
    assert len(graph.nodes) == 9
    assert nx.is_connected(graph)
    assert graph.has_edge(0, 1) and graph.has_edge(1, 2) and graph.has_edge(2, 0)
    assert graph.has_edge(3, 4) and graph.has_edge(4, 5) and graph.has_edge(5, 3)
    assert graph.has_edge(6, 7) and graph.has_edge(7, 8) and graph.has_edge(8, 6)
    assert len(graph.edges) > (3 * 3) 

def test_generate_industrial_ring_missing_params(generator):
    generator.num_switches = 6
    generator.topology_params = "{}"
    with patch.object(logger, 'error') as mock_error, \
         pytest.raises(SystemExit):
        generator._generate_industrial_ring()
    mock_error.assert_called_once()

def test_generate_tree_graph_correct_size(generator):
    generator.topology_params = "{'r': 2, 'h': 2}"
    generator.num_switches = 7 
    graph = generator._generate_tree_graph()
    assert isinstance(graph, nx.Graph)
    assert len(graph.nodes) == 7
    assert nx.is_tree(graph)

def test_generate_tree_graph_missing_params(generator):
    generator.topology_params = "{'r': 2}"
    with patch.object(logger, 'error') as mock_error, \
         pytest.raises(SystemExit):
        generator._generate_tree_graph()
    mock_error.assert_called_once()

# --- Test _get_next_port ---
def test_get_next_port_allocation(generator):
    switch_id = "SW5"
    generator.used_ports = {} 

    assert generator._get_next_port(switch_id) == 0
    assert switch_id in generator.used_ports
    
    assert generator.used_ports[switch_id] == set()

    generator.used_ports[switch_id].add(0)
    assert generator._get_next_port(switch_id) == 1

    generator.used_ports[switch_id].add(1)
    generator.used_ports[switch_id].add(3) 
    assert generator._get_next_port(switch_id) == 2

    generator.used_ports[switch_id].add(2)
    assert generator._get_next_port(switch_id) == 4

# --- Test _generate_domain_graph ---

@patch('tsn_case_gen_.domain.topology_generator.TopologyGenerator._generate_mesh_graph')
def test_generate_domain_graph_structure_and_es_distribution(mock_mesh, generator):
    mock_base = nx.Graph()
    mock_base.add_nodes_from([0, 1, 2]) 
    mock_base.add_edge(0, 1)
    mock_base.add_edge(1, 2)
    mock_mesh.return_value = mock_base

    generator.num_switches = 3 
    generator.num_end_systems = 5
    generator.topology_type = 'mesh_graph' 
    domain_id = 1 

    domain_graph = generator._generate_domain_graph(domain_id)

    switches = sorted([n for n, d in domain_graph.nodes(data=True) if d.get('type') == 'switch'])
    end_systems = sorted([n for n, d in domain_graph.nodes(data=True) if d.get('type') == 'end_system'])

    assert len(switches) == 3 
    assert len(end_systems) == 5
    assert generator.switch_counter == 3
    assert generator.node_counter == 5

    for sw_id in switches:
        assert domain_graph.nodes[sw_id]['domain'] == domain_id
        assert domain_graph.nodes[sw_id]['ports'] == 8 
        assert domain_graph.nodes[sw_id]['type'] == 'switch'
        assert sw_id in generator.used_ports 

    for es_id in end_systems:
        assert domain_graph.nodes[es_id]['domain'] == domain_id
        assert domain_graph.nodes[es_id]['type'] == 'end_system'

    assert domain_graph.has_edge(switches[0], switches[1])
    assert domain_graph.has_edge(switches[1], switches[2]) 
    assert not domain_graph.has_edge(switches[0], switches[2])

    edge_data_01 = domain_graph.get_edge_data(switches[0], switches[1])
    assert 'source_port' in edge_data_01 and isinstance(edge_data_01['source_port'], int)
    assert 'dest_port' in edge_data_01 and isinstance(edge_data_01['dest_port'], int)
    assert edge_data_01['source_port'] in generator.used_ports[switches[0]]
    assert edge_data_01['dest_port'] in generator.used_ports[switches[1]]

    es_connections = 0
    connected_switches = set()
    es_ports_on_switches = {sw_id: set() for sw_id in switches}

    for es_id in end_systems:
        neighbors = list(domain_graph.neighbors(es_id))
        assert len(neighbors) == 1
        connected_switch = neighbors[0]
        assert connected_switch in switches
        es_connections += 1
        connected_switches.add(connected_switch)

        edge_data_es = domain_graph.get_edge_data(connected_switch, es_id)
        assert 'source_port' in edge_data_es 
        assert 'dest_port' in edge_data_es and edge_data_es['dest_port'] == 0 
        assert edge_data_es['source_port'] in generator.used_ports[connected_switch]
        es_ports_on_switches[connected_switch].add(edge_data_es['source_port'])


    assert es_connections == 5

    sw0_es_ports = es_ports_on_switches.get(switches[0], set())
    sw1_es_ports = es_ports_on_switches.get(switches[1], set())
    sw2_es_ports = es_ports_on_switches.get(switches[2], set())
    assert len(sw0_es_ports) + len(sw1_es_ports) + len(sw2_es_ports) == 5
    sw1_conn_ports = {edge_data_01['dest_port'], domain_graph.get_edge_data(switches[1], switches[2])['source_port']}
    assert sw1_conn_ports.isdisjoint(sw1_es_ports)


# --- Test _get_node_domain ---

def test_get_node_domain(generator):
    g0 = nx.Graph()
    g0.add_node("SW0_d0", type="switch", domain=0)
    g0.add_node("ES0_d0", type="end_system", domain=0)

    g1 = nx.Graph()
    g1.add_node("SW1_d1", type="switch", domain=1)
    g1.add_node("ES1_d1", type="end_system", domain=1)

    generator.domain_graphs = [g0, g1]

    assert generator._get_node_domain("SW0_d0") == 0
    assert generator._get_node_domain("ES0_d0") == 0
    assert generator._get_node_domain("SW1_d1") == 1
    assert generator._get_node_domain("ES1_d1") == 1
    assert generator._get_node_domain("UnknownNode") == 0 

# --- Test Domain Connection Logic ---

@patch('random.choice', side_effect=lambda x: x[0]) 
def test_connect_domain_pair(mock_choice, generator):
    g0 = nx.Graph()
    g0.add_node("SW0_d0", type="switch", domain=0, ports=8)
    g0.add_node("SW1_d0", type="switch", domain=0, ports=8)
    g1 = nx.Graph()
    g1.add_node("SW0_d1", type="switch", domain=1, ports=8)
    mock_domain_graphs = [g0, g1]
    generator.domain_graphs = mock_domain_graphs 

    generator.used_ports["SW0_d0"] = set()
    generator.used_ports["SW1_d0"] = set()
    generator.used_ports["SW0_d1"] = set()

    topology = {"links": []} 

    generator.connections_per_domain_pair = 1
    generator.link_counter = 10 

    generator._connect_domain_pair(0, 1, mock_domain_graphs, topology)

    assert len(topology["links"]) == 2 
    assert generator.link_counter == 12 

    link_fwd = topology["links"][0]
    link_rev = topology["links"][1]

    assert link_fwd == {
        "id": "Link10",
        "source": "SW0_d0",
        "sourcePort": 0,
        "destination": "SW0_d1",
        "destinationPort": 0,
        "domain": 0,
        "connection_type": "domain_connection",
        "bandwidth_mbps": 10000,
        "delay": link_fwd["delay"]  # This is random, so we just check it exists
    }
    assert link_rev == {
        "id": "Link11",
        "source": "SW0_d1",
        "sourcePort": 0,
        "destination": "SW0_d0",
        "destinationPort": 0,
        "domain": 1,
        "connection_type": "domain_connection",
        "bandwidth_mbps": 10000,
        "delay": link_rev["delay"]  # This is random, so we just check it exists
    }

    assert generator.used_ports["SW0_d0"] == {0}
    assert generator.used_ports["SW0_d1"] == {0}
    assert generator.used_ports["SW1_d0"] == set()

    generator.connections_per_domain_pair = 2
    topology['links'] = []
    generator.used_ports["SW0_d0"] = set() 
    generator.used_ports["SW0_d1"] = set()
    generator.link_counter = 20
    mock_choice.side_effect = ["SW0_d0", "SW0_d1", "SW1_d0", "SW0_d1"]

    g1.add_node("SW1_d1", type="switch", domain=1, ports=8)
    generator.used_ports["SW1_d1"] = set()

    mock_choice.side_effect = ["SW0_d0", "SW0_d1", "SW1_d0", "SW1_d1"]

    generator._connect_domain_pair(0, 1, mock_domain_graphs, topology)

    assert len(topology["links"]) == 4 
    assert generator.link_counter == 24

    link2_fwd = topology["links"][2]
    link2_rev = topology["links"][3]
    assert link2_fwd["source"] == "SW1_d0" and link2_fwd["sourcePort"] == 0
    assert link2_fwd["destination"] == "SW1_d1" and link2_fwd["destinationPort"] == 0
    assert link2_rev["source"] == "SW1_d1" and link2_rev["sourcePort"] == 0
    assert link2_rev["destination"] == "SW1_d0" and link2_rev["destinationPort"] == 0

    assert generator.used_ports["SW0_d0"] == {0}
    assert generator.used_ports["SW0_d1"] == {0}
    assert generator.used_ports["SW1_d0"] == {0}
    assert generator.used_ports["SW1_d1"] == {0}


def test_connect_domain_pair_insufficient_switches(generator, caplog):
    g0 = nx.Graph()
    g0.add_node("SW0_d0", type="switch", domain=0, ports=8)
    g1 = nx.Graph() 
    mock_domain_graphs = [g0, g1]
    generator.domain_graphs = mock_domain_graphs
    topology = {"links": []}
    generator.connections_per_domain_pair = 1

    generator._connect_domain_pair(0, 1, mock_domain_graphs, topology)

    assert len(topology["links"]) == 0
    assert "Cannot connect domains 0 and 1: missing switches" in caplog.text


@patch('tsn_case_gen_.domain.topology_generator.TopologyGenerator._connect_domain_pair')
def test_connect_domains_line(mock_connect_pair, generator):
    generator.num_domains = 4
    mock_graphs = [MagicMock(spec=nx.Graph) for _ in range(4)]
    topology = {"links": []}

    generator._connect_domains_line(mock_graphs, topology)

    expected_calls = [
        call(0, 1, mock_graphs, topology),
        call(1, 2, mock_graphs, topology),
        call(2, 3, mock_graphs, topology),
    ]
    mock_connect_pair.assert_has_calls(expected_calls)
    assert mock_connect_pair.call_count == 3


@patch('tsn_case_gen_.domain.topology_generator.TopologyGenerator._connect_domain_pair')
def test_connect_domains_square(mock_connect_pair, generator):
    generator.num_domains = 6
    mock_graphs = [MagicMock(spec=nx.Graph) for _ in range(6)]
    topology = {"links": []}

    generator._connect_domains_square(mock_graphs, topology)

    expected_calls = [
        call(0, 1, mock_graphs, topology), call(1, 2, mock_graphs, topology),
        call(3, 4, mock_graphs, topology), call(4, 5, mock_graphs, topology),
        call(0, 3, mock_graphs, topology),
        call(1, 4, mock_graphs, topology),
        call(2, 5, mock_graphs, topology),
    ]
    mock_connect_pair.assert_has_calls(expected_calls, any_order=True)
    assert mock_connect_pair.call_count == 7 

@patch('tsn_case_gen_.domain.topology_generator.TopologyGenerator._connect_domain_pair')
def test_connect_domains_delegation(mock_connect_pair, generator):
    mock_graphs = [MagicMock()] * 2
    topology = {"links": []}

    generator.domain_connection_type = "line"
    with patch.object(generator, '_connect_domains_line') as mock_line:
        generator._connect_domains(mock_graphs, topology)
        mock_line.assert_called_once_with(mock_graphs, topology)

    generator.domain_connection_type = "square"
    with patch.object(generator, '_connect_domains_square') as mock_square:
         generator._connect_domains(mock_graphs, topology)
         mock_square.assert_called_once_with(mock_graphs, topology)

    generator.domain_connection_type = "random"
    with patch.object(generator, '_connect_domains_random') as mock_random:
         generator._connect_domains(mock_graphs, topology)
         mock_random.assert_called_once_with(mock_graphs, topology)

    generator.domain_connection_type = "unknown_type"
    with patch.object(generator, '_connect_domains_line') as mock_line:
         generator._connect_domains(mock_graphs, topology)
         mock_line.assert_called_once_with(mock_graphs, topology)


# --- Test Main generate() ---

@patch('tsn_case_gen_.domain.topology_generator.TopologyGenerator._generate_domain_graph')
@patch('tsn_case_gen_.domain.topology_generator.TopologyGenerator._connect_domains')
def test_generate_single_domain(mock_connect_domains, mock_generate_domain, generator):
    generator.num_domains = 1
    generator.delay_units = "NANO_SECOND"
    generator.default_bandwidth_mbps = 500

    mock_g = nx.Graph()
    mock_g.add_node("SW0", id="SW0", type="switch", domain=0, ports=8)
    mock_g.add_node("ES0", id="ES0", type="end_system", domain=0)
    mock_g.add_node("ES1", id="ES1", type="end_system", domain=0)
    mock_g.add_edge("SW0", "ES0", source_port=1, dest_port=0, connection_type="switch_to_end_system")
    mock_g.add_edge("SW0", "ES1", source_port=2, dest_port=0, connection_type="switch_to_end_system")
    mock_generate_domain.return_value = mock_g

    topology = generator.generate()
    mock_generate_domain.assert_called_once_with(0)
    mock_connect_domains.assert_not_called()
    
    assert topology["delay_units"] == "NANO_SECOND"
    assert topology["default_bandwidth_mbps"] == 500
    assert "switches" in topology
    assert "end_systems" in topology
    assert "links" in topology

    assert len(topology["switches"]) == 1
    assert topology["switches"][0] == {"id": "SW0", "domain": 0, "ports": 8} 
    assert len(topology["end_systems"]) == 2
    assert topology["end_systems"][0] == {"id": "ES0", "domain": 0}
    assert topology["end_systems"][1] == {"id": "ES1", "domain": 0}

    assert len(topology["links"]) == 4
    assert topology["links"][0] == {
        "id": "Link0",
        "source": "SW0",
        "destination": "ES0",
        "sourcePort": 1,
        "destinationPort": 0,
        "domain": 0,
        "bandwidth_mbps": 100,
        "delay": topology["links"][0]["delay"]  # This is random, so we just check it exists
    }

    assert topology["links"][1] == {
        "id": "Link1",
        "source": "ES0",
        "destination": "SW0",
        "sourcePort": 0,
        "destinationPort": 1,
        "domain": 0,
        "bandwidth_mbps": 100,
        "delay": topology["links"][1]["delay"]  # This is random, so we just check it exists
    }

    assert topology["links"][2] == {
        "id": "Link2",
        "source": "SW0",
        "destination": "ES1",
        "sourcePort": 2,
        "destinationPort": 0,
        "domain": 0,
        "bandwidth_mbps": 100,
        "delay": topology["links"][2]["delay"]  # This is random, so we just check it exists
    }

    assert topology["links"][3] == {
        "id": "Link3",
        "source": "ES1",
        "destination": "SW0",
        "sourcePort": 0,
        "destinationPort": 2,
        "domain": 0,
        "bandwidth_mbps": 100,
        "delay": topology["links"][3]["delay"]  # This is random, so we just check it exists
    }
    assert generator.link_counter == 4


@patch('tsn_case_gen_.domain.topology_generator.TopologyGenerator._generate_domain_graph')
@patch('tsn_case_gen_.domain.topology_generator.TopologyGenerator._connect_domains')
def test_generate_multi_domain(mock_connect_domains, mock_generate_domain, generator):

    generator.num_domains = 2
    generator.domain_connection_type = "line"

    mock_g0 = nx.Graph()
    mock_g0.add_node("SW0d0", id="SW0d0", type="switch", domain=0, ports=8)
    mock_g0.add_node("ES0d0", id="ES0d0", type="end_system", domain=0)
    mock_g0.add_edge("SW0d0", "ES0d0", source_port=1, dest_port=0)

    mock_g1 = nx.Graph()
    mock_g1.add_node("SW0d1", id="SW0d1", type="switch", domain=1, ports=8)
    mock_g1.add_node("ES0d1", id="ES0d1", type="end_system", domain=1)
    mock_g1.add_edge("SW0d1", "ES0d1", source_port=1, dest_port=0)

    mock_generate_domain.side_effect = [mock_g0, mock_g1]

    topology = generator.generate()
    mock_generate_domain.assert_has_calls([call(0), call(1)])
    assert mock_generate_domain.call_count == 2

    assert mock_connect_domains.call_count == 1

    args, kwargs = mock_connect_domains.call_args
    passed_graphs, passed_topology = args
    assert passed_graphs == [mock_g0, mock_g1] 
    assert passed_topology is topology 


    assert len(topology["switches"]) == 2 
    assert len(topology["end_systems"]) == 2 

    assert len(topology["links"]) == 4 
    assert topology["links"][0]["source"] == "SW0d0" and topology["links"][0]["destination"] == "ES0d0"
    assert topology["links"][2]["source"] == "SW0d1" and topology["links"][2]["destination"] == "ES0d1"

# --- Test get_next_port()
def test_get_next_port_connection_type_priority(generator):
    node_id = "SW_test"
    generator.used_ports[node_id] = {0}


    port = generator._get_next_port(node_id, connection_type="domain_connection")
    assert port == 1

    generator.used_ports[node_id].add(1)

    with patch.object(logger, 'warning') as mock_warn:
        port = generator._get_next_port(node_id, connection_type="domain_connection")
        assert port == 2
        mock_warn.assert_called_once()

def test_get_next_port_custom_connection_type(generator):
    node_id = "SW_test"
    generator.used_ports[node_id] = set(range(6))


    port = generator._get_next_port(node_id, connection_type="custom_type")
    assert port == 6

def test_get_next_port_all_ports_used(generator):
    node_id = "SW_test"
    generator.used_ports[node_id] = set(range(8))

    with pytest.raises(SystemExit):
        generator._get_next_port(node_id, connection_type="switch_to_switch")

def test_get_next_port_logs_warning_on_fallback(generator):
    node_id = "SW_test"

    # Use ports 0-5 which are in the priority range for switch_to_switch
    generator.used_ports[node_id] = set(range(6))

    with patch.object(logger, 'warning') as mock_warn:
        port = generator._get_next_port(node_id, connection_type="switch_to_switch")
        assert port == 6
        mock_warn.assert_called_once()
