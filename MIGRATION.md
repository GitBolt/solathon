# Migrating from Solathon 1.x to 2.0

Solathon 2 is a correctness-focused release. Most ordinary RPC calls keep their existing names, but key handling, transaction validation, dependency boundaries, and payment parsing are stricter. Review signing and Solana Pay code instead of treating this as a drop-in dependency bump.

## Runtime and installation

Python 3.11 is now the minimum supported version. `solders` is a required dependency and provides canonical native implementations for core Solana primitives.

```bash
python -m pip install --upgrade "solathon>=2,<3"
```

`qrcode` and Pillow are no longer installed for every user. Add the QR extra only in applications that render payment codes:

```bash
python -m pip install --upgrade "solathon[qr]>=2,<3"
```

Importing `solathon` or `solathon.solana_pay` no longer imports the QR stack. Calling `create_qr()` without the extra raises an `ImportError` with installation guidance.

## Public keys and keypairs

`PublicKey` is immutable and backed by `solders.Pubkey`. Its `byte_value` is now a read-only `bytes` property. Code that mutated it must construct a new key instead.

Integer construction now means a full unsigned 256-bit, big-endian value:

```python
from solathon import PublicKey

zero = PublicKey(0)
one = PublicKey(1)
```

In 1.x, only integers that happened to encode as one byte reached the length check, so integer construction was effectively unusable.

`Keypair` now uses Ed25519 key material consistently. Prefer one of the explicit constructors:

```python
from solathon import Keypair

generated = Keypair()
from_seed = Keypair.from_seed(seed_bytes)  # exactly 32 bytes
from_cli = Keypair.from_file("~/.config/solana/id.json")
from_secret = Keypair.from_private_key(secret)  # 32-byte seed or 64-byte keypair
```

For a 64-byte keypair, 2.0 verifies that the public half matches the seed. Previously accepted malformed values now raise `ValueError`. Never keep literal private-key arrays in examples, tests, or source control.

`solathon.keypair.PrivateKey` no longer subclasses `PublicKey`; it is an immutable 64-byte secret wrapper whose `str` and `repr` are redacted. Export it explicitly with `bytes(keypair)`, `bytes(keypair.private_key)`, or `keypair.private_key.base58_encode()` only at a deliberate storage boundary.

Solathon keys, messages, and transactions expose `to_solders()` and corresponding `from_solders()` constructors where useful for interoperation.

## Client lifecycle and RPC behavior

Use both clients as context managers:

```python
from solathon import Client

with Client("https://api.devnet.solana.com") as client:
    print(client.get_health())
```

```python
from solathon import AsyncClient

async with AsyncClient("https://api.devnet.solana.com") as client:
    print(await client.get_health())
```

The clients now support an explicit timeout, injected `httpx` clients, deterministic `close()`, and ordered JSON-RPC batches. An injected HTTP client remains owned by the caller and is not closed by Solathon.

RPC parameter encoding is recursive: nested `PublicKey` objects become base58 strings and nested `bytes` become base64. Requests always include a `params` array. Current config fields such as `min_context_slot`, data slices, encodings, and version gates are available on their corresponding methods.

With `clean_response=True` (the default), RPC envelopes are unwrapped and typed result wrappers are returned where the API defines one. With `clean_response=False`, the complete JSON-RPC envelope is preserved. `RPCRequestError` now retains the node's `code`, `data`, error object, and full response.

The old async spelling `build_and_send_request_async()` remains available, while `build_and_send_request()` is now the matching sync/async name for new code.

### Transaction-version reads

`get_block()` and `get_transaction()` continue to default to `max_supported_transaction_version=0`. This safely supports legacy and v0 data. Opt into v1 only when your reader is prepared for the experimental v1 message shape:

```python
transaction = client.get_transaction(
    signature,
    max_supported_transaction_version=1,
)
```

As of September 2026, v1 is not active on public clusters. The gate above prepares a reader; it does not make v1 safe to submit before cluster activation.

After activation, an unprepared `getTransaction` call—or an entire `getBlock` result containing one v1 transaction—can fail with RPC error `-32015`. Prefer `encoding="base64"` when your application decodes v1 wire bytes, particularly above the legacy 1,232-byte limit.

## Legacy and versioned transactions

Legacy `Transaction` compilation now orders the fee payer and account metadata canonically, derives required signers from instructions, validates supplied signatures against the message, handles partial signatures explicitly, and enforces Solana's 1,232-byte packet limit. Invalid or incomplete input now generally raises `TypeError` or `ValueError` instead of incidental `AttributeError`, `IndexError`, or `RuntimeError`.

Construction remains familiar, and omitted signer lists no longer crash the constructor:

```python
transaction = Transaction(
    fee_payer=payer.public_key,
    signers=[payer],
    instructions=[instruction],
)
```

`add_instructions()` now returns the transaction, so it can be chained. `serialize(require_all_signatures=False)` supports workflows that intentionally transport a partially signed transaction; every signature that is present is still verified.

2.0 adds `MessageV0`, `AddressLookupTableAccount`, and `VersionedTransaction`. Fetch a blockhash and its validity height together when compiling v0:

```python
latest = client.get_latest_blockhash(commitment="confirmed")
message = MessageV0.compile(
    payer=payer.public_key,
    instructions=[instruction],
    recent_blockhash=latest.blockhash,
    lookup_tables=lookup_tables,
)
transaction = VersionedTransaction(message, [payer])
```

2.0 also includes experimental `MessageV1` and `TransactionConfig` support for local Agave 4.2 testing. V1 has no ALTs, uses a 4,096-byte limit, and puts execution limits in its signed message config. Solathon requires explicit positive compute-unit and loaded-account-data limits and rejects Compute Budget instructions in v1 because the runtime ignores them. The v1 `priority_fee` is total lamports, not micro-lamports per compute unit.

## Confirmation and expiration

Do not confirm a transaction with a fixed sleep. Use its `lastValidBlockHeight`:

```python
transaction = Transaction(
    fee_payer=payer.public_key,
    signers=[payer],
    instructions=[instruction],
)
signature = client.send_and_confirm_transaction(
    transaction,
    commitment="confirmed",
    options={"preflightCommitment": "confirmed"},
)
```

When the transaction has no blockhash, `send_and_confirm_transaction()` fetches the blockhash and its validity height together. When it already has a blockhash—including v0 transactions—pass the matching height:

```python
signature = client.send_and_confirm_transaction(
    transaction,
    commitment="confirmed",
    last_valid_block_height=latest.last_valid_block_height,
    options={"preflightCommitment": "confirmed"},
)
```

The method signs and sends exactly once, then polls status until the requested commitment is reached, the validity height is exceeded, or an optional timeout expires. Expiration and on-chain failures raise `RPCRequestError` with diagnostic data.

Durable-nonce transactions are the exception: they have no last-valid block
height. Pass a finite `timeout`; Solathon will not compare them against an
unrelated recent blockhash's validity window.

Construct them with `NonceInformation(nonce, nonce_instruction)`. Solathon
validates the nonce value and compiles the required advance instruction first,
matching the runtime's durable-nonce detection rule.

## Amount conversion

`sol_to_lamport()` no longer truncates fractional lamports or silently accepts non-finite values. It accepts `Decimal`, strings, integers, and floats through exact decimal text conversion, and raises if the result is not an unsigned whole lamport.

```python
from decimal import Decimal
from solathon.utils import lamport_to_sol_decimal, sol_to_lamport

assert sol_to_lamport(Decimal("0.000000001")) == 1
assert lamport_to_sol_decimal(1) == Decimal("0.000000001")
```

`lamport_to_sol()` remains available for compatibility and returns `float`; use `lamport_to_sol_decimal()` when precision matters.

## SPL Token and Token-2022

2.0 adds a deliberately limited token primitive layer:

- Token and Token-2022 program constants
- Program-aware ATA derivation and idempotent ATA creation
- Exact UI-amount conversion and `TransferChecked` construction
- Base mint/account parsing and opaque Token-2022 TLV records
- A batched `get_all_token_accounts_by_owner()` query across both programs

Always pass the actual token program when deriving an ATA or building an instruction. An address derived for the classic Token program is different from the address derived for Token-2022.

This is not a complete Token-2022 client. Pass parsed mint/account states via the `extensions` argument when building a generic transfer. Transfer-fee, transfer-hook, non-transferable, and unknown future extensions are rejected when a generic transfer cannot apply their semantics safely; parsers still preserve opaque TLV records for inspection. Extension-specific operations remain the application's responsibility.

## Solana Pay

The URL and parsed-value types are intentionally stricter:

- Amounts parse to `Decimal`, not `float`.
- Recipients, mints, and references parse to `PublicKey` values.
- `reference` is always an ordered list (possibly empty), rather than a string-or-list union.
- Multiple references, `memo`, and `spl-token` are preserved.
- Native SOL cannot exceed nine decimal places.
- Transaction-request links must be absolute HTTPS URLs without credentials or fragments.

Update code such as:

```python
from decimal import Decimal

request = parse_url(url)
assert request.amount == Decimal("0.01")
for reference in request.reference:
    index_payment(reference)
```

`create_transfer()` and `validate_transfer()` support native SOL, classic SPL Token, and basic Token-2022 payments. Token construction fetches and validates the mint plus both program-aware associated token accounts and uses `TransferChecked`. It fails closed for transfer-fee, transfer-hook, transformed-UI-amount, non-transferable, paused, or unknown extensions; an enabled incoming-memo requirement is honored when a memo is supplied. Validation checks the final instruction, mint, destination ATA, exact base-unit amount, ordered references, and the recipient's recorded token-balance increase.

`fetch_transaction()` now expects the Solana Pay transaction response to contain standard base64 wire bytes and validates size, signer requirements, existing signatures, and HTTPS transport before returning it. Treat the returned transaction as untrusted application input and show its details to the signer.

## Upgrade checklist

1. Move production to Python 3.11+ and update the lock file.
2. Install `[qr]` only where QR images are rendered.
3. Remove literal private keys and verify every persisted 64-byte keypair loads successfully.
4. Run wire-format and signature tests for every transaction your application builds.
5. Replace fixed confirmation sleeps with `send_and_confirm_transaction()` or `confirm_transaction()` plus `last_valid_block_height`.
6. Update Solana Pay annotations and comparisons for `Decimal`, `PublicKey`, and list-valued references.
7. Query and derive token accounts with the correct Token or Token-2022 program ID.
8. Keep RPC transaction-version reads at `0` unless the consumer is deliberately v1-ready; do not send v1 on public clusters before activation.
