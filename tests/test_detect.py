from unittest.mock import Mock, patch

import pytest
import requests

from abb_robot_client import RWS, RWS2, connect


def _answering(**status_by_url):
    """Patch HTTP so only the given base URLs respond (with the given status); everything else is unreachable."""
    def get(self, url, **kwargs):
        base = url.rstrip("/")
        if base not in status_by_url:
            raise requests.ConnectionError(base)
        return Mock(status_code=status_by_url[base])

    return patch.object(requests.Session, "get", get)


def test_detects_rws2_on_443():
    with _answering(**{"https://h:443": 200}):
        client = connect("h")
    assert isinstance(client, RWS2)
    assert client.base_url == "https://h:443"


def test_detects_rws1_on_80():
    with _answering(**{"http://h:80": 200}):
        client = connect("h")
    assert type(client) is RWS
    assert client.base_url == "http://h:80"


def test_prefers_earlier_port():
    with _answering(**{"http://h:80": 200, "https://h:5466": 200}):
        client = connect("h", ports=[5466, 80])
    assert client.base_url == "https://h:5466"


def test_unreachable_raises():
    with _answering(), pytest.raises(ConnectionError, match="No RWS1/RWS2 controller answered"):
        connect("h")


def test_wrong_credentials_raises_auth_error():
    with _answering(**{"http://h:80": 401}), pytest.raises(ConnectionError, match="rejected username 'u'"):
        connect("h", username="u", password="bad")
