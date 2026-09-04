"""Build a legacy SOL transfer; submit only with an explicit --send flag."""

from __future__ import annotations

import argparse
import base64
import os

from solathon import Client, Keypair, PublicKey, Transaction
from solathon.core.instructions import transfer


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rpc-url",
        default=os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com"),
    )
    parser.add_argument("--keypair", default=os.environ.get("SOLANA_KEYPAIR"))
    parser.add_argument("--recipient", default=os.environ.get("SOLANA_RECIPIENT"))
    parser.add_argument("--lamports", type=int, default=10_000)
    parser.add_argument(
        "--send",
        action="store_true",
        help="submit and confirm instead of printing a dry-run payload",
    )
    args = parser.parse_args()
    if not args.keypair:
        parser.error("set SOLANA_KEYPAIR or pass --keypair")
    if not args.recipient:
        parser.error("set SOLANA_RECIPIENT or pass --recipient")
    if args.lamports <= 0:
        parser.error("--lamports must be positive")
    return args


def main() -> None:
    args = arguments()
    sender = Keypair.from_file(args.keypair)
    recipient = PublicKey(args.recipient)
    transaction = Transaction(
        fee_payer=sender.public_key,
        signers=[sender],
        instructions=[transfer(sender.public_key, recipient, args.lamports)],
    )

    with Client(args.rpc_url) as client:
        if not args.send:
            latest = client.get_latest_blockhash(commitment="confirmed")
            transaction.recent_blockhash = latest.blockhash
            encoded = base64.b64encode(
                transaction.serialize(
                    require_all_signatures=False,
                    verify_signatures=False,
                )
            ).decode("ascii")
            print("Dry run only; transaction was not submitted.")
            print("last valid block height:", latest.last_valid_block_height)
            print("unsigned base64 wire transaction:", encoded)
            return

        signature = client.send_and_confirm_transaction(
            transaction,
            commitment="confirmed",
            options={"preflightCommitment": "confirmed"},
        )
        print("confirmed signature:", signature)


if __name__ == "__main__":
    main()
