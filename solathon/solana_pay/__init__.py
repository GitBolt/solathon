"""Solana Pay helpers, loaded lazily to keep optional QR dependencies optional."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .create_qr import create_qr
    from .create_transfer import create_transfer
    from .encode_url import encode_url
    from .fetch_transaction import fetch_transaction
    from .find_reference import find_reference
    from .parse_url import parse_url
    from .validate_transfer import validate_transfer

__all__ = [
    "create_qr",
    "create_transfer",
    "encode_url",
    "fetch_transaction",
    "find_reference",
    "parse_url",
    "validate_transfer",
]

_EXPORT_MODULES = {name: f".{name}" for name in __all__}


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
