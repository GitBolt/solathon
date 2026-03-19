from __future__ import annotations

from typing import Any, Dict
from .publickey import PublicKey
from nacl.signing import VerifyKey
from solathon.core.types import Commitment, RPCErrorType, RPCResponse

class RPCRequestError(Exception):
    def __init__(self, message="Failed to fetch data from RPC endpoint"):
        self.message = message
        super().__init__(self.message)


LAMPORT_PER_SOL: int = 1000000000
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
            f"Invalid commitment value. Allowed values are {allowed_commitments}")

    return {"commitment": value}

def lamport_to_sol(lamports: int) -> float:
    return truncate_float(lamports * SOL_PER_LAMPORT, SOL_FLOATING_PRECISION)


def sol_to_lamport(sol: float | int) -> int:
    return int(sol * LAMPORT_PER_SOL)


def verify_signature(
    public_key: PublicKey | str,
    signature: list,
    message: bytes | str | None = None
) -> None:

    if not message:
        message = public_key.base58_encode()

    if isinstance(public_key, str):
        public_key = PublicKey(public_key)

    if isinstance(message, str):
        message = bytes(message, encoding="utf8")

    bytes_pk = bytes(public_key)
    vk = VerifyKey(bytes_pk)
    vk.verify(message, bytes(signature))


def clean_response(response: RPCResponse) -> Dict[str, Any] | RPCErrorType:
    if "error" in response:
        return response["error"]

    result = response["result"]

    if isinstance(result, dict):
        result.pop("context", None)
        result.pop("id", None)
        if "value" in result:
            return result["value"]

    return result
