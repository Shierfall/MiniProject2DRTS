import pytest

@pytest.fixture
def simple_topology_multi_domain():
    """Fixture providing a simple multi-domain topology for testing."""
    return {
        "end_systems": [
            {"id": "ES0", "domain": 0},
            {"id": "ES1", "domain": 0},
            {"id": "ES2", "domain": 1},
            {"id": "ES3", "domain": 1}
        ],
        "switches": [
            {"id": "SW0", "domain": 0, "ports": 8},
            {"id": "SW1", "domain": 1, "ports": 8}
        ],
        "links": []
    } 