#!/usr/bin/env python
"""
Command-line interface for Tool-Set servers.

Usage
-----
toolset-server run my_module:MyToolSet [--host 0.0.0.0] [--port 9000] [--reload]

This module is installed as a console-script entry-point named
`toolset-server` (see section 2).
"""
from __future__ import annotations
import argparse, importlib, sys
from typing import Type

from toolsetserver.runtime import ToolSetServer

# --------------------------------------------------------------------
# Utility: dynamic import "pkg.mod:ClassName" → the actual class object
# --------------------------------------------------------------------
def _import_class(dotted: str) -> Type[ToolSetServer]:
    mod_path, sep, cls_name = dotted.partition(":")
    if not sep:
        sys.exit("❌  Specify server as 'module:ClassName' (colon‑separated).")
    try:
        module = importlib.import_module(mod_path)
        cls = getattr(module, cls_name)
    except (ModuleNotFoundError, AttributeError) as e:
        sys.exit(f"❌  Cannot import '{dotted}': {e}")
    if not issubclass(cls, ToolSetServer):
        sys.exit(f"❌  {dotted} is not a ToolSetServer subclass.")
    return cls

# --------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="toolset-server",
        description="Run or inspect ToolSetServer subclasses.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- run ----
    run_p = sub.add_parser("run", help="Start a ToolSetServer.")
    run_p.add_argument("server", help="Import path 'module:ClassName'.")
    run_p.add_argument("--host", default=None, help="Override host.")
    run_p.add_argument("--port", type=int, default=None, help="Override port.")
    run_p.add_argument("--reload", action="store_true",
                       help="Enable auto‑reload (development only).")

    # ---- list ----  (optional little helper)
    list_p = sub.add_parser("list", help="Show all @tool_method endpoints.")
    list_p.add_argument("server", help="Import path 'module:ClassName'.")

    args = parser.parse_args()

    if args.command == "run":
        cls = _import_class(args.server)
        # Override host/port if provided
        if args.host: cls.host = args.host
        if args.port: cls.port = args.port
        uvicorn_kwargs = {"reload": args.reload} if args.reload else {}
        cls.serve(**uvicorn_kwargs)

    elif args.command == "list":
        cls = _import_class(args.server)
        print(f"🛠  Tools exposed by {cls.__name__}:")
        for route in cls._fastapi.routes:
            if route.path.startswith("/tools/"):
                print(f"  • {route.path}")
