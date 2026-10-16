from unittest.mock import patch

import pytest

from abb_robot_client import RWS, RWS2, connect


def _answering(*urls):
    """Patch both clients' ping so only the given base URLs respond."""
    def ping(self, timeout=1.0):
        return self.base_url in urls

    return patch.object(RWS, "ping", ping), patch.object(RWS2, "ping", ping)


def test_detects_rws2_on_443():
    p1, p2 = _answering("https://h:443")
    with p1, p2:
        client = connect("h")
    assert isinstance(client, RWS2)
    assert client.base_url == "https://h:443"


def test_detects_rws1_on_80():
    p1, p2 = _answering("http://h:80")
    with p1, p2:
        client = connect("h")
    assert type(client) is RWS
    assert client.base_url == "http://h:80"


def test_prefers_earlier_port():
    p1, p2 = _answering("http://h:80", "https://h:5466")
    with p1, p2:
        client = connect("h", ports=[5466, 80])
    assert client.base_url == "https://h:5466"


def test_unreachable_raises():
    p1, p2 = _answering()
    with p1, p2, pytest.raises(ConnectionError):
        connect("h")
