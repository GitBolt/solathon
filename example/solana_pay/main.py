"""Create and parse a Solana Pay request without moving funds."""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from solathon import Keypair, PublicKey
from solathon.solana_pay import encode_url, parse_url

DEFAULT_MERCHANT = "mvines9iiHiQTysrwkJjGf2gb9Ex9jXJX8ns3qwf2kN"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merchant", default=DEFAULT_MERCHANT)
    parser.add_argument("--amount", type=Decimal, default=Decimal("0.01"))
    parser.add_argument("--memo", default="order-001234")
    parser.add_argument(
        "--qr",
        type=Path,
        help="write a PNG QR code (requires the solathon[qr] extra)",
    )
    return parser.parse_args()


def main() -> None:
    args = arguments()
    merchant = PublicKey(args.merchant)

    # Generate one reference per checkout and persist the public key with the
    # order. The ephemeral private key is neither needed nor printed.
    reference = Keypair().public_key
    url = encode_url(
        recipient=merchant,
        amount=args.amount,
        reference=reference,
        label="Example store",
        message="Order 001234",
        memo=args.memo,
    )
    request = parse_url(url)

    print("payment URL:", url)
    print("exact amount:", request.amount)
    print("reference:", request.reference[0])
    print("No transaction was created or submitted.")

    if args.qr is not None:
        from solathon.solana_pay import create_qr

        args.qr.write_bytes(create_qr(url).getvalue())
        print("QR image:", args.qr)


if __name__ == "__main__":
    main()
