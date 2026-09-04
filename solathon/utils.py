from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from nacl.signing import VerifyKey

from solathon.core.types import Commitment, RPCResponse

from .publickey import PublicKey


class RPCRequestError(Exception):
    def __init__(
        self,
        message: str = "Failed to fetch data from RPC endpoint",
        code: int | None = None,
        data: Any = None,
        *,
        response: Any = None,
        error: Any = None,
    ):
        self.message = message
        self.code = code
        self.data = data
        self.response = response
        self.error = error
        super().__init__(self.message)


LAMPORT_PER_SOL: int = 1000000000
MAX_LAMPORTS: int = 2**64 - 1
SOL_PER_LAMPORT: float = 1 / LAMPORT_PER_SOL
SOL_FLOATING_PRECISION: int = 9


def truncate_float(number: float, length: int) -> float:
    number = number * pow(10, length)
    number = int(number)
    number = float(number)
    number /= pow(10, length)
    return number


def validate_commitment(value: Commitment) -> dict:
    allowed_commitments = {"processed", "confirmed", "finalized"}

    if value not in allowed_commitments:
        raise ValueError(
            f"Invalid commitment value. Allowed values are {allowed_commitments}"
        )

    return {"commitment": value}


def unwrap_rpc_response(response: RPCResponse) -> Any:
    if not isinstance(response, dict):
        raise RPCRequestError(
            "RPC response was not a JSON object", data=response, response=response
        )
    error = response.get("error")
    if error:
        raise RPCRequestError(
            f"RPC Error {error.get('code')}: {error.get('message')}",
            code=error.get("code"),
            data=error.get("data"),
            response=response,
            error=error,
        )
    if "result" not in response:
        raise RPCRequestError(
            "RPC response did not include a result", response=response
        )
    return response["result"]


def lamport_to_sol(lamports: int) -> float:
    if isinstance(lamports, bool) or not isinstance(lamports, int):
        raise TypeError("Lamports must be an integer")
    return float(lamport_to_sol_decimal(lamports))


def lamport_to_sol_decimal(lamports: int) -> Decimal:
    """Convert lamports to SOL without losing precision."""

    if isinstance(lamports, bool) or not isinstance(lamports, int):
        raise TypeError("Lamports must be an integer")
    if not 0 <= lamports <= MAX_LAMPORTS:
        raise ValueError("Lamports must fit in an unsigned 64-bit integer")
    return Decimal(lamports) / Decimal(LAMPORT_PER_SOL)


def sol_to_lamport(sol: Decimal | float | int | str) -> int:
    if isinstance(sol, bool):
        raise TypeError("SOL amount must be numeric")
    try:
        amount = Decimal(str(sol))
    except (InvalidOperation, ValueError) as error:
        raise TypeError("SOL amount must be numeric") from error
    if not amount.is_finite():
        raise ValueError("SOL amount must be finite")
    lamports = amount * LAMPORT_PER_SOL
    if lamports != lamports.to_integral_value():
        raise ValueError("SOL amount cannot contain fractional lamports")
    value = int(lamports)
    if not 0 <= value <= MAX_LAMPORTS:
        raise ValueError("SOL amount must fit in an unsigned 64-bit lamport value")
    return value


def verify_signature(
    public_key: PublicKey | str,
    signature: bytes | bytearray | Sequence[int],
    message: bytes | str | None = None,
) -> None:
    if isinstance(public_key, str):
        public_key = PublicKey(public_key)

    if message is None:
        message = public_key.base58_encode()

    if isinstance(message, str):
        message = bytes(message, encoding="utf8")

    bytes_pk = bytes(public_key)
    vk = VerifyKey(bytes_pk)
    vk.verify(message, bytes(signature))


def clean_response(response: RPCResponse) -> Any:
    result = unwrap_rpc_response(response)

    if isinstance(result, dict):
        if "value" in result:
            return result["value"]
        return {
            key: value for key, value in result.items() if key not in {"context", "id"}
        }

    return result
