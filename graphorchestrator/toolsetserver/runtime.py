from __future__ import annotations
import json, uvicorn
from typing import Any, List, Callable
from fastapi import FastAPI, Response, Depends, Header, HTTPException
from pydantic import BaseModel, Field

# Import core types
from graphorchestrator.core.state import State
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


# Pydantic model to parse incoming JSON
# BaseModel class for state management in the ToolSetServer.
class StateModel(BaseModel):
    """
    Represents the state model for messages.

    Attributes:
        messages (List[Any]): A list to store messages of any type.
    """

    messages: List[Any] = Field(default_factory=list)


# Metaclass that registers FastAPI endpoints
class _ToolSetMeta(type):
    """
    Metaclass responsible for registering FastAPI endpoints.

    It automatically scans methods of the ToolSetServer for those marked as 'tool_method' and creates corresponding API routes.
    """

    def __new__(mcls, name, bases, ns):
        cls = super().__new__(mcls, name, bases, ns)
        cls._fastapi = FastAPI(title=getattr(cls, "name", name))
        cls._tool_index = []

        # Auth dependency (optional)
        if getattr(cls, "require_auth", False):

            async def _check(
                auth: str | None = Header(default=None, alias="Authorization")
            ) -> None:
                """
                Dependency to check authentication token.

                Args:
                    auth (str | None): The authorization token passed in the header.

                Raises:
                    HTTPException: If authentication fails.
                """
                if not auth or not cls.authenticate(auth):
                    raise HTTPException(status_code=401, detail="Unauthorized")

        else:

            async def _check():
                return None

        # Tool method to FastAPI route
        def make_endpoint(fn: Callable):
            """
            Decorator function to create an endpoint for a given tool method.

            Args:
                fn (Callable): The tool method function.

            Returns:
                Callable: The wrapped endpoint function.

            Raises:
                HTTPException: If an error occurs during tool execution.
            """

            async def endpoint(payload: StateModel, _=Depends(_check)):
                log = GraphLogger.get()
                state_in = State(messages=payload.messages)

                log.info(
                    **wrap_constants(
                        message="Tool method invoked",
                        **{
                            LC.EVENT_TYPE: "tool",
                            LC.ACTION: "tool_invoked",
                            LC.NODE_ID: fn.__name__,
                            LC.INPUT_SIZE: len(state_in.messages),
                        },
                    )
                )

                try:
                    result = await fn(state_in)
                except HTTPException as e:
                    raise  # re-raise to preserve HTTP semantics
                except Exception as e:
                    log.error(
                        **wrap_constants(
                            message="Tool method execution failed",
                            **{
                                LC.EVENT_TYPE: "tool",
                                LC.ACTION: "tool_failed",
                                LC.NODE_ID: fn.__name__,
                                LC.CUSTOM: {"error": str(e)},
                            },
                        )
                    )
                    return Response(
                        content=str(e), status_code=500, media_type="text/plain"
                    )

                log.info(
                    **wrap_constants(
                        message="Tool method execution succeeded",
                        **{
                            LC.EVENT_TYPE: "tool",
                            LC.ACTION: "tool_success",
                            LC.NODE_ID: fn.__name__,
                            LC.OUTPUT_SIZE: len(result.messages),
                            LC.SUCCESS: True,
                        },
                    )
                )

                return Response(
                    content=json.dumps({"messages": result.messages}),
                    media_type="application/json",
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
                cls._tool_index.append(
                    {
                        "name": attr_name,
                        "path": route_path,
                        "doc": (attr_val.__doc__ or "").strip(),
                    }
                )

        # Tool catalog
        @cls._fastapi.get("/tools")
        async def _catalog():
            """
            Endpoint to list all available tools.

            Returns:
                List[dict]: A list of dictionaries, each describing a tool, including its name, path, and documentation.

            """
            return cls._tool_index

        return cls


# Base class to be subclassed by users
class ToolSetServer(metaclass=_ToolSetMeta):
    """
    Base class for creating a tool set server.

    This class handles the creation of FastAPI endpoints for registered tool methods.
    """

    host: str = "127.0.0.1"
    port: int = 8000
    name: str = "ToolSet"
    require_auth: bool = False

    @classmethod
    # Class method to handle authentication.
    def authenticate(cls, token: str) -> bool:
        """
        Authenticates a request based on the provided token.

        Args:
            token (str): The authentication token.

        Returns:
            bool: True if the token is valid, False otherwise.
        """
        return False

    @classmethod
    def serve(cls, **uvicorn_kwargs: Any):
        """
        Starts the FastAPI server synchronously.

        Args:
            **uvicorn_kwargs: Keyword arguments to pass to uvicorn.run.

        Raises:
            RuntimeError: If there's an error during server start-up.
        """
        uvicorn.run(
            cls._fastapi,
            host=uvicorn_kwargs.pop("host", cls.host),
            port=uvicorn_kwargs.pop("port", cls.port),
            log_level=uvicorn_kwargs.pop("log_level", "info"),
            **uvicorn_kwargs,
        )

    @classmethod
    async def serve_async(cls, **uvicorn_kwargs: Any):
        """
        Starts the FastAPI server asynchronously.

        Args:
            **uvicorn_kwargs: Keyword arguments to pass to uvicorn.run.
        Raises:
            RuntimeError: If there's an error during server start-up.
        """
        config = uvicorn.Config(
            cls._fastapi,
            host=uvicorn_kwargs.pop("host", cls.host),
            port=uvicorn_kwargs.pop("port", cls.port),
            log_level=uvicorn_kwargs.pop("log_level", "info"),
            **uvicorn_kwargs,
        )
        server = uvicorn.Server(config)
        await server.serve()


__all__ = ["ToolSetServer"]
