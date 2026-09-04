from __future__ import annotations

import base64
import sys
from collections.abc import Mapping
from typing import Any, cast

import httpx

from .. import __version__
from ..publickey import PublicKey
from .types import RPCResponse


def _encode_param(value: Any) -> Any:
    if isinstance(value, PublicKey):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, tuple):
        return [_encode_param(item) for item in value]
    if isinstance(value, list):
        return [_encode_param(item) for item in value]
    if isinstance(value, dict):
        return {key: _encode_param(item) for key, item in value.items()}
    return value


def _request_headers() -> dict[str, str]:
    version = sys.version_info
    return {
        "Content-Type": "application/json",
        "User-Agent": (
            "Solathon (https://github.com/GitBolt/solathon "
            f"{__version__}) Python{version[0]}.{version[1]}"
        ),
    }


class RequestBuilder:
    def __init__(self) -> None:
        self.request_id = 0

    def build_data(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> dict[str, Any]:
        if not method:
            raise ValueError("RPC method cannot be empty")

        self.request_id += 1
        data: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": _encode_param(
                [] if params is None or params == [None] else params
            ),
        }
        return data

    def reset(self) -> None:
        self.request_id = 0


class HTTPClient(RequestBuilder):
    """Synchronous HTTP transport for Solana JSON-RPC."""

    def __init__(
        self,
        endpoint: str,
        timeout: float = 30.0,
        *,
        client: httpx.Client | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__()
        self.endpoint = endpoint
        self.timeout = timeout
        self.headers = {**_request_headers(), **dict(headers or {})}
        self._owns_client = client is None
        self.client = client or self._new_client()

    def _new_client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout)

    def send(self, data: dict[str, Any]) -> RPCResponse:
        response = self.client.post(
            url=self.endpoint,
            headers=self.headers,
            json=data,
        )
        response.raise_for_status()
        return cast(RPCResponse[Any], response.json())

    def send_batch(self, batch: list[dict[str, Any]]) -> list[RPCResponse]:
        if not batch:
            return []
        response = self.client.post(
            url=self.endpoint,
            headers=self.headers,
            json=batch,
        )
        response.raise_for_status()
        return cast(list[RPCResponse[Any]], response.json())

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def refresh(self) -> None:
        if self._owns_client:
            self.close()
            self.client = self._new_client()
        self.reset()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncHTTPClient(RequestBuilder):
    """Asynchronous HTTP transport for Solana JSON-RPC."""

    def __init__(
        self,
        endpoint: str,
        timeout: float = 30.0,
        *,
        client: httpx.AsyncClient | None = None,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__()
        self.endpoint = endpoint
        self.timeout = timeout
        self.headers = {**_request_headers(), **dict(headers or {})}
        self._owns_client = client is None
        self.client = client or self._new_client()

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout)

    async def send(self, data: dict[str, Any]) -> RPCResponse:
        response = await self.client.post(
            url=self.endpoint,
            headers=self.headers,
            json=data,
        )
        response.raise_for_status()
        return cast(RPCResponse[Any], response.json())

    async def send_batch(
        self,
        batch: list[dict[str, Any]],
    ) -> list[RPCResponse]:
        if not batch:
            return []
        response = await self.client.post(
            url=self.endpoint,
            headers=self.headers,
            json=batch,
        )
        response.raise_for_status()
        return cast(list[RPCResponse[Any]], response.json())

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def refresh(self) -> None:
        if self._owns_client:
            await self.close()
            self.client = self._new_client()
        self.reset()

    async def __aenter__(self) -> AsyncHTTPClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
