import json
import threading
import urllib.error
import urllib.request

import pytest

from donga_app.server import create_server


@pytest.fixture
def base_url():
    server = create_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def get_json(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, json.loads(response.read())


def test_healthz_returns_ok(base_url):
    status, body = get_json(f"{base_url}/healthz")
    assert status == 200
    assert body["status"] == "ok"


def test_root_returns_greeting(base_url):
    status, body = get_json(f"{base_url}/")
    assert status == 200
    assert body["message"] == "Hello, world!"


def test_unknown_path_returns_404(base_url):
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{base_url}/nope", timeout=5)
    assert exc_info.value.code == 404
