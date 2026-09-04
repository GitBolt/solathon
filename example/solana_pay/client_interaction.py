"""Safe wallet-side construction helpers; this module never submits funds."""

from __future__ import annotations

from solathon import Client, Keypair, Transaction
from solathon.solana_pay import create_transfer, parse_url
from solathon.solana_pay.types import CreateTransferFields, TransferRequestURL


def build_wallet_transaction(
    client: Client,
    url: str,
    sender: Keypair,
) -> Transaction:
    """Build a SOL or token payment transaction for wallet review."""

    request = parse_url(url)
    if not isinstance(request, TransferRequestURL):
        raise ValueError("Expected a Solana Pay transfer request")
    if request.amount is None:
        raise ValueError("The payment request does not specify an amount")
    fields: CreateTransferFields = {
        "recipient": request.recipient,
        "amount": request.amount,
        "reference": request.reference,
    }
    if request.memo is not None:
        fields["memo"] = request.memo
    if request.spl_token is not None:
        fields["spl_token"] = request.spl_token

    return create_transfer(client, sender, fields, commitment="confirmed")
