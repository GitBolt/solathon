"""Build and sign v0 and experimental v1 transactions without submitting."""

from __future__ import annotations

import os

from solathon import (
    Client,
    Keypair,
    MessageV0,
    MessageV1,
    TransactionConfig,
    VersionedTransaction,
)
from solathon.core.instructions import transfer

RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")


def main() -> None:
    payer = Keypair()
    recipient = Keypair().public_key

    with Client(RPC_URL) as client:
        latest = client.get_latest_blockhash(commitment="confirmed")

    instruction = transfer(payer.public_key, recipient, 10_000)
    v0_message = MessageV0.compile(
        payer=payer.public_key,
        instructions=[instruction],
        recent_blockhash=latest.blockhash,
        lookup_tables=[],
    )
    v0_transaction = VersionedTransaction(v0_message, [payer])
    v0_transaction.sign()
    print("v0 wire bytes:", len(v0_transaction.serialize()))
    print("v0 last valid block height:", latest.last_valid_block_height)

    # V1 is not active on public clusters as of September 2026. Build it only
    # for format migration work or a v1-enabled local Agave 4.2+ validator.
    v1_message = MessageV1.compile(
        payer=payer.public_key,
        instructions=[instruction],
        recent_blockhash=latest.blockhash,
        config=TransactionConfig(
            compute_unit_limit=200_000,
            loaded_accounts_data_size_limit=64 * 1024,
            priority_fee=5_000,  # total lamports, not micro-lamports per CU
        ),
    )
    v1_transaction = VersionedTransaction(v1_message, [payer])
    v1_transaction.sign()
    print("v1 wire bytes (not submitted):", len(v1_transaction.serialize()))


if __name__ == "__main__":
    main()
