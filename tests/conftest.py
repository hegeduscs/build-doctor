"""Teszt-infrastruktúra: a mock CI egy háttérszálon indul véletlen porton, az MCP szerver ezt használja."""
import importlib
import os
import socket
import threading
import time

import httpx
import pytest
import uvicorn


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def ci_url(tmp_path_factory):
    os.environ["DATA_DIR"] = str(tmp_path_factory.mktemp("mockci"))
    from mock_ci.app import app

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            if httpx.get(f"{url}/health").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield url
    server.should_exit = True


@pytest.fixture(scope="session")
def mcp_server(ci_url, tmp_path_factory):
    os.environ["CI_API_URL"] = ci_url
    os.environ["AUDIT_LOG"] = str(tmp_path_factory.mktemp("audit") / "audit.jsonl")
    os.environ.setdefault("WRITE_MODE", "dry-run")
    import ci_tools_mcp.server as srv

    return importlib.reload(srv)
