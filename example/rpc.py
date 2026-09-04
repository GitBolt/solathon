"""Read-only synchronous and asynchronous RPC examples."""

from __future__ import annotations

import asyncio
import os

from solathon import AsyncClient, Client, PublicKey

RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
OWNER = PublicKey(
    os.environ.get(
        "SOLANA_OWNER",
        "B3BhJ1nvPvEhx3hq3nfK8hx4WYcKZdbhavSobZEA44ai",
    )
)


def sync_example() -> None:
    with Client(RPC_URL) as client:
        balance, version = client.send_batch(
            [
                ("getBalance", [str(OWNER), {"commitment": "confirmed"}]),
                ("getVersion", []),
            ]
        )
        print("sync balance:", balance["value"])
        print("sync version:", version)


async def async_example() -> None:
    async with AsyncClient(RPC_URL) as client:
        balance, version = await asyncio.gather(
            client.get_balance(OWNER, commitment="confirmed"),
            client.get_version(),
        )
        print("async balance:", balance)
        print("async version:", version)


if __name__ == "__main__":
    sync_example()
    asyncio.run(async_example())
