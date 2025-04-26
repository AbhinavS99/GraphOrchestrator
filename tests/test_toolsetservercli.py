import sys
from click.testing import CliRunner
from graphorchestrator.toolsetserver.__main__ import cli
from graphorchestrator.toolsetserver.runtime import ToolSetServer
from graphorchestrator.decorators.actions import tool_method


class DummyRunServer(ToolSetServer):
    pass  # We will monkey-patch `serve`


class DummyListServer(ToolSetServer):
    @tool_method
    def foo(self, state):
        return state

    @tool_method
    async def bar(self, state):
        return state


def test_run_command_invokes_serve(monkeypatch):
    runner = CliRunner()
    called = {}

    def fake_serve(cls, **uvicorn_kwargs):
        called["cls"] = cls
        called["uvicorn_kwargs"] = uvicorn_kwargs

    monkeypatch.setattr(DummyRunServer, "serve", classmethod(fake_serve))

    module_path = __name__
    result = runner.invoke(
        cli,
        [
            "run",
            f"{module_path}:DummyRunServer",
            "--host",
            "0.0.0.0",
            "--port",
            "4242",
            "--reload",
        ],
    )

    assert result.exit_code == 0
    assert called["cls"] is DummyRunServer
    assert DummyRunServer.host == "0.0.0.0"
    assert DummyRunServer.port == 4242
    assert called["uvicorn_kwargs"] == {"reload": True}


def test_list_command_prints_tools(capsys):
    runner = CliRunner()
    module_path = __name__
    result = runner.invoke(cli, ["list", f"{module_path}:DummyListServer"])
    assert result.exit_code == 0
    assert "Tools exposed by DummyListServer" in result.output
    assert "• /tools/foo" in result.output
    assert "• /tools/bar" in result.output


def test_invalid_server_format():
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "invalidformat"])
    assert result.exit_code != 0
    assert "Specify server as 'module:ClassName'" in result.output


def test_import_nonexistent_class():
    runner = CliRunner()
    result = runner.invoke(
        cli, ["run", "graphorchestrator.toolsetserver.runtime:NonExistentClass"]
    )
    assert result.exit_code != 0
    assert "Cannot import" in result.output


class NotAServer:
    pass


def test_import_wrong_type(monkeypatch):
    module_name = __name__
    monkeypatch.setitem(sys.modules, module_name, sys.modules[__name__])
    setattr(sys.modules[module_name], "NotAServer", NotAServer)

    runner = CliRunner()
    result = runner.invoke(cli, ["run", f"{module_name}:NotAServer"])
    assert result.exit_code != 0
    assert "is not a ToolSetServer subclass" in result.output


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "run" in result.output
    assert "list" in result.output
