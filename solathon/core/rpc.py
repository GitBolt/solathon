from __future__ import annotations

from typing import Any, cast

from ..utils import RPCRequestError
from .types import BlockHash, Commitment, SignatureStatus

_COMMITMENT_RANK: dict[Commitment, int] = {
    "processed": 0,
    "confirmed": 1,
    "finalized": 2,
}

DEFAULT_BLOCKHASH = "11111111111111111111111111111111"


class RPCResponseError(RPCRequestError):
    """RPC failure retaining the original error object and response envelope."""

    def __init__(
        self,
        message: str,
        *,
        response: Any,
        error: Any = None,
        code: int | None = None,
        data: Any = None,
    ):
        super().__init__(
            message,
            code=code,
            data=data,
            response=response,
            error=error,
        )


def unwrap_rpc_envelope(response: Any) -> Any:
    """Unwrap a JSON-RPC result while retaining the exact failing envelope."""
    if not isinstance(response, dict):
        raise RPCResponseError(
            "RPC response was not a JSON object",
            response=response,
            data=response,
        )
    rpc_error = response.get("error")
    if rpc_error:
        raise RPCResponseError(
            f"RPC Error {rpc_error.get('code')}: {rpc_error.get('message')}",
            response=response,
            error=rpc_error,
            code=rpc_error.get("code"),
            data=rpc_error.get("data"),
        )
    if "result" not in response:
        raise RPCResponseError(
            "RPC response did not include a result", response=response
        )
    return response["result"]


def signature_status_payload(
    response: Any, clean_response: bool
) -> dict[str, Any] | None:
    """Normalize getSignatureStatuses without discarding its raw status fields."""
    result = response if clean_response else unwrap_rpc_envelope(response)
    if isinstance(result, dict):
        result = result.get("value")
    if not isinstance(result, list) or not result:
        raise RPCRequestError("RPC returned an invalid signature status response")
    status = result[0]
    if status is None:
        return None
    if isinstance(status, SignatureStatus):
        return cast(dict[str, Any], status.raw)
    if isinstance(status, dict):
        return status
    raise RPCRequestError("RPC returned an invalid signature status entry")


def block_height_value(response: Any, clean_response: bool) -> int:
    result = response if clean_response else unwrap_rpc_envelope(response)
    if isinstance(result, bool) or not isinstance(result, int):
        raise RPCRequestError("RPC returned an invalid block height")
    return result


def latest_blockhash_value(
    response: Any, clean_response: bool
) -> tuple[str, int | None]:
    result = response if clean_response else unwrap_rpc_envelope(response)
    if isinstance(result, BlockHash):
        return result.blockhash, result.last_valid_block_height
    if isinstance(result, dict) and "value" in result:
        result = result["value"]
    if not isinstance(result, dict) or not isinstance(result.get("blockhash"), str):
        raise RPCRequestError("RPC returned an invalid latest blockhash response")
    last_valid_block_height = result.get("lastValidBlockHeight")
    if last_valid_block_height is not None and (
        isinstance(last_valid_block_height, bool)
        or not isinstance(last_valid_block_height, int)
    ):
        raise RPCRequestError("RPC returned an invalid last valid block height")
    return result["blockhash"], last_valid_block_height


def transaction_signature_value(response: Any, clean_response: bool) -> str:
    result = response if clean_response else unwrap_rpc_envelope(response)
    if not isinstance(result, str):
        raise RPCRequestError("RPC returned an invalid transaction signature")
    return result


def response_context_slot(response: Any, clean_response: bool) -> int | None:
    if clean_response:
        context = getattr(response, "context", None)
    else:
        result = unwrap_rpc_envelope(response)
        context = result.get("context") if isinstance(result, dict) else None
    if not isinstance(context, dict):
        return None
    slot = context.get("slot")
    if slot is None:
        return None
    if isinstance(slot, bool) or not isinstance(slot, int):
        raise RPCRequestError("RPC returned an invalid context slot")
    return slot


def token_program_ids() -> tuple[str, str]:
    """Load SPL program IDs lazily to keep RPC-client imports dependency-light."""
    from ..token import TOKEN_2022_PROGRAM_ID, TOKEN_PROGRAM_ID

    return str(TOKEN_PROGRAM_ID), str(TOKEN_2022_PROGRAM_ID)


def commitment_reached(status: dict[str, Any], commitment: Commitment) -> bool:
    reported_value = status.get("confirmationStatus")
    if reported_value not in _COMMITMENT_RANK:
        confirmations = status.get("confirmations")
        if confirmations is None:
            reported: Commitment = "finalized"
        elif confirmations > 0:
            reported = "confirmed"
        else:
            reported = "processed"
    else:
        reported = cast(Commitment, reported_value)
    return _COMMITMENT_RANK[reported] >= _COMMITMENT_RANK[commitment]


def validate_confirmation_polling(timeout: float | None, poll_interval: float) -> None:
    if timeout is not None and timeout < 0:
        raise ValueError("timeout cannot be negative")
    if poll_interval < 0:
        raise ValueError("poll_interval cannot be negative")
