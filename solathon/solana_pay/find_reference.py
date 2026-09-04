from __future__ import annotations

from ..client import Client
from ..core.types import Commitment, TransactionSignature
from ..publickey import PublicKey
from ..utils import unwrap_rpc_response


def find_reference(
    client: Client,
    reference: PublicKey,
    *,
    commitment: Commitment | None = None,
    limit: int = 1000,
    before: str | None = None,
    until: str | None = None,
) -> TransactionSignature:
    """Find the oldest signature indexed for a Solana Pay reference.

    ``before`` and ``until`` mirror the RPC pagination window. The helper
    continues backward within that window until it reaches the oldest result.
    """

    if not isinstance(reference, PublicKey):
        raise TypeError("reference must be a PublicKey")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise ValueError("limit must be an integer from 1 through 1000")
    for name, value in (("before", before), ("until", until)):
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"{name} must be a non-empty signature string")

    cursor = before
    oldest = None
    while True:
        response = client.get_signatures_for_address(
            str(reference),
            limit=limit,
            before=cursor,
            until=until,
            commitment=commitment,
        )
        if isinstance(response, dict):
            response = [
                TransactionSignature(value) for value in unwrap_rpc_response(response)
            ]
        if not response:
            if oldest is None:
                raise ValueError("Reference not found")
            return oldest
        oldest = response[-1]
        if len(response) < limit:
            return oldest
        next_before = oldest.signature
        if next_before == cursor:
            raise ValueError("Reference signature pagination did not advance")
        cursor = next_before
