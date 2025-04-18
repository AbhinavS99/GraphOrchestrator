from __future__ import annotations
import asyncio, json, uvicorn
from typing import Any, Dict, List, Callable
from fastapi import FastAPI, Response, Depends, Header, HTTPException
from pydantic import BaseModel, Field

# Import core types
from graphorchestrator.core.state import State
from graphorchestrator.decorators.actions import tool_method

# Pydantic model to parse incoming JSON
class StateModel(BaseModel):
    messages: List[Any] = Field(default_factory=list)

# Metaclass that registers FastAPI endpoints
class _ToolSetMeta(type):
    def __new__(mcls, name, bases, ns):
        cls = super().__new__(mcls, name, bases, ns)
        cls._fastapi = FastAPI(title=getattr(cls, "name", name))
        cls._tool_index = []

        # Auth dependency (optional)
        if getattr(cls, "require_auth", False):
            async def _check(auth: str | None = Header(default=None, alias="Authorization")):
                if not auth or not cls.authenticate(auth):
                    raise HTTPException(status_code=401, detail="Unauthorized")
        else:
            async def _check():
                return None

        # Tool method to FastAPI route
        def make_endpoint(fn: Callable):
            async def endpoint(payload: StateModel, _=Depends(_check)):
                state_in = State(messages=payload.messages)
                try:
                    result = await fn(state_in)
                except HTTPException:
                    # preserve HTTP errors
                    raise
                except Exception as e:
                    # return exception message on 500
                    return Response(content=str(e), status_code=500, media_type="text/plain")
                return Response(
                    content=json.dumps({"messages": result.messages}),
                    media_type="application/json"
                )
            return endpoint

        # Scan for tools (including inherited)
        for attr_name in dir(cls):
            if attr_name.startswith("_"):
                continue
            attr_val = getattr(cls, attr_name)
            if callable(attr_val) and getattr(attr_val, "is_tool_method", False):
                route_path = f"/tools/{attr_name}"
                cls._fastapi.post(route_path)(make_endpoint(attr_val))
                cls._tool_index.append({
                    "name": attr_name,
                    "path": route_path,
                    "doc": (attr_val.__doc__ or "").strip()
                })

        # Tool catalog
        @cls._fastapi.get("/tools")
        async def _catalog():
            return cls._tool_index

        return cls

# Base class to be subclassed by users
class ToolSetServer(metaclass=_ToolSetMeta):
    host: str = "127.0.0.1"
    port: int = 8000
    name: str = "ToolSet"
    require_auth: bool = False

    @classmethod
    def authenticate(cls, token: str) -> bool:
        return False

    @classmethod
    def serve(cls, **uvicorn_kwargs: Any):
        uvicorn.run(
            cls._fastapi,
            host=uvicorn_kwargs.pop("host", cls.host),
            port=uvicorn_kwargs.pop("port", cls.port),
            log_level=uvicorn_kwargs.pop("log_level", "info"),
            **uvicorn_kwargs
        )

    @classmethod
    async def serve_async(cls, **uvicorn_kwargs: Any):
        config = uvicorn.Config(
            cls._fastapi,
            host=uvicorn_kwargs.pop("host", cls.host),
            port=uvicorn_kwargs.pop("port", cls.port),
            log_level=uvicorn_kwargs.pop("log_level", "info"),
            **uvicorn_kwargs
        )
        server = uvicorn.Server(config)
        await server.serve()

__all__ = ["ToolSetServer"]
