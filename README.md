<p align="center">
  <img alt="Solathon logo" src="https://solathon.vercel.app/solathon.svg" width="120">
</p>

<h1 align="center">Solathon</h1>

<p align="center">
  A compact, typed Solana SDK for Python with matching synchronous and asynchronous APIs.
</p>

<p align="center">
  <a href="https://pypi.org/project/solathon/"><img src="https://badge.fury.io/py/solathon.svg" alt="PyPI version"></a>
  <a href="https://github.com/GitBolt/solathon/actions/workflows/tests.yml"><img src="https://github.com/GitBolt/solathon/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/GitBolt/solathon/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="MIT License"></a>
</p>

Solathon 2 provides pooled JSON-RPC clients, Solana key and wire primitives, legacy and v0 transactions, experimental v1 support, System and Compute Budget instructions, safe SPL Token/Token-2022 primitives, and Solana Pay helpers. Canonical key, message, signature, and transaction operations are backed by [`solders`](https://pypi.org/project/solders/).

## Requirements

- Python 3.11 or newer
- An HTTP(S) Solana JSON-RPC endpoint

## Installation

```bash
pip install solathon
```

QR rendering is deliberately optional:

```bash
pip install "solathon[qr]"
```

Upgrading from 1.x? Read the [2.0 migration guide](https://github.com/GitBolt/solathon/blob/master/MIGRATION.md) before moving signing or payment code into production.

## RPC clients

Responses are unwrapped from the JSON-RPC envelope by default. Use a context manager so the pooled HTTP connection is closed deterministically.

```python
from solathon import Client, PublicKey

owner = PublicKey("B3BhJ1nvPvEhx3hq3nfK8hx4WYcKZdbhavSobZEA44ai")

with Client("https://api.devnet.solana.com") as client:
    balance = client.get_balance(owner, commitment="confirmed")
    latest = client.get_latest_blockhash(commitment="confirmed")

print(balance)
print(latest.blockhash, latest.last_valid_block_height)
```

The async client mirrors the sync method names and parameter shapes:

```python
import asyncio

from solathon import AsyncClient


async def main() -> None:
    async with AsyncClient("https://api.devnet.solana.com") as client:
        version, health = await asyncio.gather(
            client.get_version(),
            client.get_health(),
        )
        print(version, health)


asyncio.run(main())
```

Set `clean_response=False` when you need the complete JSON-RPC envelope. RPC failures raise `RPCRequestError`; its `code`, `data`, `error`, and `response` attributes retain the node's diagnostics. `send_batch()` sends several methods in one HTTP request and returns results in request order.

## Send and confirm safely

`send_and_confirm_transaction()` confirms against the block height returned with the transaction's blockhash. This is safer than assuming a fixed number of seconds because blockhashes expire by block height.

The following example sends real lamports to the configured cluster (devnet by default). It intentionally reads the keypair and recipient from the environment—never put private-key bytes in source control.

```python
import os

from solathon import Client, Keypair, PublicKey, Transaction
from solathon.core.instructions import transfer

sender = Keypair.from_file(os.environ["SOLANA_KEYPAIR"])
recipient = PublicKey(os.environ["SOLANA_RECIPIENT"])
transaction = Transaction(
    fee_payer=sender.public_key,
    signers=[sender],
    instructions=[transfer(sender.public_key, recipient, 10_000)],
)

with Client(
    os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
) as client:
    signature = client.send_and_confirm_transaction(
        transaction,
        commitment="confirmed",
        options={"preflightCommitment": "confirmed"},
    )

print(signature)
```

If a transaction already has a recent blockhash, pass the matching `last_valid_block_height` explicitly. Fetch both values together and use the same commitment for blockhash selection, preflight, and confirmation:

```python
latest = client.get_latest_blockhash(commitment="confirmed")
transaction.recent_blockhash = latest.blockhash
signature = client.send_and_confirm_transaction(
    transaction,
    commitment="confirmed",
    last_valid_block_height=latest.last_valid_block_height,
    options={"preflightCommitment": "confirmed"},
)
```

Durable-nonce transactions have no last-valid block height. For those,
`send_and_confirm_transaction()` requires a finite `timeout` and never applies
an unrelated recent-blockhash expiry check.

See Solana's [confirmation and expiration guide](https://solana.com/developers/cookbook/transactions/confirmation) for the underlying lifecycle.

## Legacy, v0, and v1 transactions

`Transaction` builds the legacy format. Legacy and v0 transactions request resource limits and priority through Compute Budget instructions; put them before application instructions:

```python
from solathon.core.compute_budget import (
    set_compute_unit_limit,
    set_compute_unit_price,
)

instructions = [
    set_compute_unit_limit(200_000),
    set_compute_unit_price(5_000),  # micro-lamports per compute unit
    transfer(payer.public_key, recipient, 10_000),
]
```

`MessageV0` adds Address Lookup Tables (ALTs) and keeps the 1,232-byte transaction limit:

```python
from solathon import Client, Keypair, MessageV0, PublicKey, VersionedTransaction
from solathon.core.instructions import transfer

payer = Keypair.from_file("~/.config/solana/id.json")
recipient = PublicKey("B3BhJ1nvPvEhx3hq3nfK8hx4WYcKZdbhavSobZEA44ai")

with Client("https://api.devnet.solana.com") as client:
    latest = client.get_latest_blockhash(commitment="confirmed")
    message = MessageV0.compile(
        payer=payer.public_key,
        instructions=[transfer(payer.public_key, recipient, 10_000)],
        recent_blockhash=latest.blockhash,
        lookup_tables=[],
    )
    transaction = VersionedTransaction(message, [payer])
    signature = client.send_and_confirm_transaction(
        transaction,
        commitment="confirmed",
        last_valid_block_height=latest.last_valid_block_height,
        options={"preflightCommitment": "confirmed"},
    )
```

`AddressLookupTableAccount.from_account_data()` decodes an on-chain ALT account for v0 compilation. Solathon objects also provide `to_solders()`/`from_solders()` interoperability where relevant.

### Experimental v1

As of September 2026, transaction format v1 is **not active on any public Solana cluster**; activation is targeted for Agave 4.2. Solathon can build, sign, parse, and serialize v1 for local validator testing and migration work, but production applications must not submit it until their target cluster activates the format. Track the [official versioned-transaction documentation](https://solana.com/docs/core/transactions/versioned-transactions) for activation status.

```python
from solathon import MessageV1, TransactionConfig, VersionedTransaction

config = TransactionConfig(
    compute_unit_limit=200_000,
    loaded_accounts_data_size_limit=64 * 1024,
    priority_fee=5_000,  # total lamports in v1, not micro-lamports per CU
)
message = MessageV1.compile(
    payer=payer.public_key,
    instructions=[transfer(payer.public_key, recipient, 10_000)],
    recent_blockhash=latest.blockhash,
    config=config,
)
transaction = VersionedTransaction(message, [payer])
transaction.sign()
wire_bytes = transaction.serialize()  # local testing only for now
```

Important v1 differences:

- Both `compute_unit_limit` and `loaded_accounts_data_size_limit` are required and must be positive.
- `priority_fee` is a total lamport amount. It is not `SetComputeUnitPrice`'s micro-lamports-per-CU value.
- Compute Budget instructions are ignored by the v1 runtime, so Solathon rejects them in `MessageV1`; set values on `TransactionConfig`.
- v1 has no ALTs and allows up to 4,096 bytes with addresses inline.
- RPC readers still default to `max_supported_transaction_version=0`. Opt into `1` deliberately when preparing a v1-aware reader: `client.get_transaction(signature, max_supported_transaction_version=1)`.

## SPL Token and Token-2022 primitives

Solathon can query accounts from both token programs in one batch, derive program-aware associated token addresses, create idempotent ATA instructions, build checked transfers, and parse base mint/account state plus Token-2022 TLV extensions.

```python
import os
from decimal import Decimal

from solathon import Client, PublicKey
from solathon.token import (
    TOKEN_2022_PROGRAM_ID,
    get_associated_token_address,
    token_amount_to_base_units,
    transfer_checked,
)

owner = PublicKey(os.environ["TOKEN_OWNER"])
mint = PublicKey(os.environ["TOKEN_2022_MINT"])
source = get_associated_token_address(owner, mint, TOKEN_2022_PROGRAM_ID)
destination = PublicKey(os.environ["TOKEN_DESTINATION_ACCOUNT"])
amount = token_amount_to_base_units(Decimal("1.25"), decimals=9)

instruction = transfer_checked(
    source,
    mint,
    destination,
    owner,
    amount,
    decimals=9,
    token_program_id=TOKEN_2022_PROGRAM_ID,
)

with Client("https://api.mainnet-beta.solana.com") as client:
    accounts = client.get_all_token_accounts_by_owner(owner, commitment="confirmed")
```

This is intentionally a small, safe primitive layer—not a complete Token-2022 SDK. Parse relevant mint and account data and pass the resulting states through `transfer_checked(..., extensions=[mint_state, account_state])`. Generic transfers reject transfer-fee, transfer-hook, non-transferable, and unknown future extensions when their semantics cannot be applied safely. Parsers still preserve unknown TLV records for inspection. Extension-specific creation, fee calculation, hook resolution, confidential transfers, and metadata/group operations are outside the current scope. See the official [Token extension guide](https://solana.com/docs/tokens/extensions).

## Solana Pay

Use `Decimal` for amounts. Parsing also returns `Decimal`, so values do not pass through binary floating point. Multiple references retain their order.

```python
from decimal import Decimal

from solathon import Keypair, PublicKey
from solathon.solana_pay import encode_url, parse_url

merchant = PublicKey("mvines9iiHiQTysrwkJjGf2gb9Ex9jXJX8ns3qwf2kN")
reference = Keypair().public_key  # unique per checkout; store it with the order
url = encode_url(
    recipient=merchant,
    amount=Decimal("0.01"),
    reference=reference,
    memo="order-42",
)
request = parse_url(url)
```

With the QR extra installed:

```python
from pathlib import Path

from solathon.solana_pay import create_qr

Path("payment.png").write_bytes(create_qr(url).getvalue())
```

Native SOL, classic SPL Token, and basic Token-2022 transfer creation and validation are supported. Token payments derive both parties' program-aware associated token accounts, use an exact `TransferChecked` amount, and verify the recipient's balance increase. Pay construction fails closed for transfer-fee, transfer-hook, transformed-UI-amount, non-transferable, paused, and unknown Token-2022 extensions; required incoming memos are honored when supplied. Transaction-request links must use HTTPS, and fetched transactions are treated as untrusted. See the canonical [Solana Pay specification](https://github.com/solana-foundation/pay/blob/main/typescript/packages/solana-pay/docs/src/SPEC.md).

## Examples and development

Runnable, secret-free examples live in the [example directory](https://github.com/GitBolt/solathon/tree/master/example). State-changing examples require explicit environment variables and a `--send` flag.
Development and release commands require Poetry 2.4.2 or newer.

```bash
poetry install --with dev --all-extras
poetry run ruff format --check .
poetry run ruff check .
poetry run pytest
poetry run pip-audit
poetry check --lock
poetry build
```

See the [changelog](https://github.com/GitBolt/solathon/blob/master/CHANGELOG.md) for release details and the [contributing guide](https://github.com/GitBolt/solathon/blob/master/CONTRIBUTING.md) for contributor setup.
