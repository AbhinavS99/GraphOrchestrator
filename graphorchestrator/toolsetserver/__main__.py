#!/usr/bin/env python
import importlib
import click
from typing import Type
from graphorchestrator.toolsetserver.runtime import ToolSetServer


def _import_class(dotted: str) -> Type[ToolSetServer]:
    mod_path, sep, cls_name = dotted.partition(":")
    if not sep:
        raise click.ClickException("❌ Specify server as 'module:ClassName'")
    try:
        module = importlib.import_module(mod_path)
        cls = getattr(module, cls_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise click.ClickException(f"❌ Cannot import '{dotted}': {e}")
    if not issubclass(cls, ToolSetServer):
        raise click.ClickException(f"❌ {dotted} is not a ToolSetServer subclass.")
    return cls


@click.group()
def cli():
    """Run or inspect ToolSetServer subclasses."""
    pass


@cli.command()
@click.argument("server")
@click.option("--host", default=None, help="Override host.")
@click.option("--port", type=int, default=None, help="Override port.")
@click.option("--reload", is_flag=True, help="Enable auto-reload (development only).")
def run(server, host, port, reload):
    """Start a ToolSetServer."""
    cls = _import_class(server)
    if host:
        cls.host = host
    if port:
        cls.port = port
    uvicorn_kwargs = {"reload": reload} if reload else {}
    cls.serve(**uvicorn_kwargs)


@cli.command()
@click.argument("server")
def list(server):
    """Show all @tool_method endpoints."""
    cls = _import_class(server)
    click.echo(f"🛠  Tools exposed by {cls.__name__}:")
    for route in cls._fastapi.routes:
        if route.path.startswith("/tools/"):
            click.echo(f"  • {route.path}")


if __name__ == "__main__":
    cli()
