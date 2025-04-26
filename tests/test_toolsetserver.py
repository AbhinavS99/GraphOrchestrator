import asyncio
import pytest
import httpx
from contextlib import asynccontextmanager
from uvicorn import Config, Server
import threading

from graphorchestrator.toolsetserver.runtime import ToolSetServer
from graphorchestrator.core.state import State
from graphorchestrator.decorators.actions import tool_method
from graphorchestrator.nodes.nodes import ToolSetNode
from graphorchestrator.core.retry import RetryPolicy
from graphorchestrator.graph.builder import GraphBuilder
from graphorchestrator.graph.executor import GraphExecutor


# ────────────────────────────────
# OPEN server (no auth required)
# ────────────────────────────────
class OpenTools(ToolSetServer):
    host, port = "127.0.0.1", 9100

    @tool_method
    def ping(state: State) -> State:
        state.messages.append("pong")
        return state


# ────────────────────────────────
# SECURE server (auth required)
# ────────────────────────────────
class SecureTools(ToolSetServer):
    host, port = "127.0.0.1", 9101
    require_auth = True
    _TOKENS = {"secret-123"}

    @classmethod
    def authenticate(cls, token: str) -> bool:
        return token in cls._TOKENS

    @tool_method
    async def hello(state: State) -> State:
        state.messages.append("hi")
        return state


# ────────────────────────────────
# Async Uvicorn context wrapper
# ────────────────────────────────
@asynccontextmanager
async def _spawn_server(server_cls):
    config = Config(
        server_cls._fastapi,
        host=server_cls.host,
        port=server_cls.port,
        log_level="warning",
        lifespan="on",  # or "auto" / "off" — doesn’t matter here
    )
    server = Server(config)

    thread = threading.Thread(target=server.run)
    thread.start()

    # Wait for the server to start up
    while not server.started:
        await asyncio.sleep(0.1)

    try:
        yield
    finally:
        server.should_exit = True
        thread.join()


# ────────────────────────────────
# TEST: Open server
# ────────────────────────────────
@pytest.mark.asyncio
async def test_01_open_server_tool_and_catalog():
    async with _spawn_server(OpenTools):
        async with httpx.AsyncClient() as client:
            # Catalog
            cat = await client.get("http://127.0.0.1:9100/tools")
            assert cat.status_code == 200
            assert any(tool["name"] == "ping" for tool in cat.json())

            # Tool call
            res = await client.post(
                "http://127.0.0.1:9100/tools/ping", json={"messages": []}
            )
            assert res.status_code == 200
            assert res.json() == {"messages": ["pong"]}


# ────────────────────────────────
# TEST: Auth-required server
# ────────────────────────────────
@pytest.mark.asyncio
async def test_02_secure_server_authorized_and_unauthorized():
    async with _spawn_server(SecureTools):
        async with httpx.AsyncClient() as client:
            url = "http://127.0.0.1:9101/tools/hello"

            # Unauthorized
            r1 = await client.post(url, json={"messages": []})
            assert r1.status_code == 401

            # Authorized
            r2 = await client.post(
                url, headers={"Authorization": "secret-123"}, json={"messages": []}
            )
            assert r2.status_code == 200
            assert r2.json() == {"messages": ["hi"]}


# 1. 404 for missing tool
class MissingTools(ToolSetServer):
    host, port = "127.0.0.1", 9120

    @tool_method
    def foo(state: State) -> State:
        state.messages.append("foo")
        return state


@pytest.mark.asyncio
async def test_03_404_tool_not_found():
    async with _spawn_server(MissingTools):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://127.0.0.1:9120/tools/not_exists", json={"messages": []}
            )
            assert r.status_code == 404


# 2. 422 for malformed JSON
@pytest.mark.asyncio
async def test_04_malformed_json():
    async with _spawn_server(MissingTools):
        async with httpx.AsyncClient() as client:
            # Send plain text instead of JSON
            r = await client.post("http://127.0.0.1:9120/tools/foo", content="not json")
            assert r.status_code == 422


# 3. Tool returns non-State -> 500
class BadReturnTools(ToolSetServer):
    host, port = "127.0.0.1", 9121

    @tool_method
    def bad(state: State) -> State:
        return 123  # wrong type


@pytest.mark.asyncio
async def test_05_tool_returns_non_state():
    async with _spawn_server(BadReturnTools):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://127.0.0.1:9121/tools/bad", json={"messages": []}
            )
            assert r.status_code == 500
            assert "Tool method must return a state" in r.text


# 4. Catalog includes correct docstrings
class DocTools(ToolSetServer):
    host, port = "127.0.0.1", 9122

    @tool_method
    def doc_tool(state: State) -> State:
        """This is a test doc."""
        state.messages.append("docged")
        return state

    @tool_method
    async def async_doc(state: State) -> State:
        """Async docstring here."""
        state.messages.append("asyncged")
        return state


@pytest.mark.asyncio
async def test_06_catalog_docs_and_paths():
    async with _spawn_server(DocTools):
        async with httpx.AsyncClient() as client:
            cat = await client.get("http://127.0.0.1:9122/tools")
            assert cat.status_code == 200
            tools = {t["name"]: t for t in cat.json()}
            assert tools["doc_tool"]["doc"] == "This is a test doc."
            assert tools["doc_tool"]["path"] == "/tools/doc_tool"
            assert tools["async_doc"]["doc"] == "Async docstring here."


# 5. Concurrent requests
@pytest.mark.asyncio
async def test_07_concurrent_requests():
    class ConcurTools(OpenTools):
        host, port = "127.0.0.1", 9123

    async with _spawn_server(ConcurTools):
        async with httpx.AsyncClient() as client:

            async def call_ping():
                r = await client.post(
                    "http://127.0.0.1:9123/tools/ping", json={"messages": []}
                )
                assert r.status_code == 200
                assert r.json() == {"messages": ["pong"]}

            # fire 10 concurrent requests
            await asyncio.gather(*(call_ping() for _ in range(10)))


@pytest.mark.asyncio
async def test_08_toolsetnode_basic_invocation(monkeypatch):
    # Stub httpx.AsyncClient so that it always returns a 200 with messages+["pong"]
    class DummyResponse:
        def __init__(self, data):
            self._data = data
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json, timeout):
            # echo back existing messages + "pong"
            return DummyResponse({"messages": json["messages"] + ["pong"]})

    monkeypatch.setattr(
        "graphorchestrator.nodes.nodes.ToolSetNode.httpx.AsyncClient", DummyClient
    )

    node = ToolSetNode(node_id="t1", base_url="http://fake", tool_name="ping")
    inp = State(messages=["hello"])
    out = await node.execute(inp)
    assert out.messages == ["hello", "pong"]


@pytest.mark.asyncio
async def test_09_toolsetnode_retries_exhausted_raises(monkeypatch):
    # Always fail
    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json, timeout):
            raise httpx.RequestError("permanent failure")

    monkeypatch.setattr(
        "graphorchestrator.nodes.nodes.ToolSetNode.httpx.AsyncClient", DummyClient
    )

    node = ToolSetNode("t3", "http://fake", "pong")
    with pytest.raises(httpx.RequestError):
        await node.execute(State(messages=[]))


# ──────────────────────────────────────────────────────────────────────────────
# Utilities for stubbing httpx.AsyncClient
# ──────────────────────────────────────────────────────────────────────────────
class DummyResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._data


class DummyClientBase:
    """Base AsyncClient stub; override post() in subclasses."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


# ──────────────────────────────────────────────────────────────────────────────
# 1) Basic invocation: ToolSetNode should append "pong"
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_10_toolsetnode_basic_invocation(monkeypatch):
    # Stub httpx.AsyncClient so post(...) always echoes + ["pong"]
    class DummyClient(DummyClientBase):
        async def post(self, url, json, timeout):
            return DummyResponse({"messages": json["messages"] + ["pong"]})

    # Monkeypatch the AsyncClient used by ToolSetNode
    monkeypatch.setattr(
        "graphorchestrator.nodes.nodes.httpx.AsyncClient", DummyClient, raising=True
    )

    node = ToolSetNode(
        node_id="call_tool",
        base_url="http://example.com/api/",
        tool_name="foo",
    )

    # ensure trailing slash was stripped
    assert node.base_url.endswith("api")
    assert node.base_url == "http://example.com/api"

    # Execute and verify output
    in_state = State(messages=["hello"])
    out_state = await node.execute(in_state)
    assert out_state.messages == ["hello", "pong"]


@pytest.mark.asyncio
async def test_11_toolsetnode_raises(monkeypatch):
    class DummyClient(DummyClientBase):
        async def post(self, url, json, timeout):
            raise Exception("permanent failure")

    monkeypatch.setattr(
        "graphorchestrator.nodes.nodes.httpx.AsyncClient", DummyClient, raising=True
    )

    node = ToolSetNode("n", "http://x", "foo")

    with pytest.raises(Exception) as exc:
        await node.execute(State(messages=[]))
    assert "permanent failure" in str(exc.value)


# ──────────────────────────────────────────────────────────────────────────────
# 4) Integration: use ToolSetNode inside a GraphExecutor
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_12_toolsetnode_integration_with_graphexecutor(monkeypatch):
    # stub to append ["pong"] to whatever arrives
    class DummyClient(DummyClientBase):
        async def post(self, url, json, timeout):
            return DummyResponse({"messages": json["messages"] + ["pong"]})

    monkeypatch.setattr(
        "graphorchestrator.nodes.nodes.httpx.AsyncClient", DummyClient, raising=True
    )

    builder = GraphBuilder()
    ts_node = ToolSetNode("ts", "http://svc", "foo")
    builder.add_node(ts_node)
    builder.add_concrete_edge("start", "ts")
    builder.add_concrete_edge("ts", "end")

    graph = builder.build_graph()
    executor = GraphExecutor(graph, State(messages=["A"]))
    final = await executor.execute()
    assert final.messages == ["A", "pong"]


# ──────────────────────────────────────────────────────────────────────────────
# 5) Concurrency: many ToolSetNode calls in parallel still work
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_13_toolsetnode_concurrent_execution(monkeypatch):
    class DummyClient(DummyClientBase):
        async def post(self, url, json, timeout):
            # simulate variable latency
            await asyncio.sleep(0.001)
            return DummyResponse({"messages": json["messages"] + ["X"]})

    monkeypatch.setattr(
        "graphorchestrator.nodes.nodes.httpx.AsyncClient", DummyClient, raising=True
    )

    node = ToolSetNode("n", "http://svc", "foo")

    async def call():
        out = await node.execute(State(messages=["p"]))
        assert out.messages == ["p", "X"]

    # fire 20 concurrent calls
    await asyncio.gather(*(call() for _ in range(20)))
