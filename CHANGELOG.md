# Changelog

All notable changes to Solathon are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [2.0.0] - Unreleased

This is a substantial modernization release. See [MIGRATION.md](MIGRATION.md) for application-level upgrade guidance.

### Added

- Canonical `solders` interoperability and native validation/serialization for core Solana key, message, signature, and transaction operations.
- `MessageV0`, `VersionedTransaction`, Address Lookup Table compilation, ALT account-data decoding, partial signing, and round-trip parsing.
- Experimental `MessageV1` and inline `TransactionConfig` support for local Agave 4.2 testing. Public clusters do not yet accept v1.
- Block-height-aware `confirm_transaction()` and `send_and_confirm_transaction()` on both sync and async clients.
- Durable-nonce-aware confirmation that requires a finite timeout instead of applying an unrelated recent-blockhash expiry height.
- Typed `NonceInformation` construction that places the required nonce-advance instruction first.
- Ordered JSON-RPC batching, injectable `httpx` transports, configurable timeouts, and deterministic sync/async context management.
- Current RPC configuration fields, including data slices, minimum context slots, binary encodings, loaded-address response data, and explicit transaction-version gates.
- Program-aware SPL Token and Token-2022 ATA derivation, idempotent ATA creation, checked-transfer construction, exact amount conversion, base account/mint parsers, and opaque TLV extension records.
- Solana Pay creation and economic validation for native SOL, classic SPL Token, and basic Token-2022 transfers.
- A batched `get_all_token_accounts_by_owner()` helper that queries both token programs.
- Current System Program instructions for nonce upgrades and prefunded account creation, plus complete seeded and durable-nonce builders.
- Typed package marker (`py.typed`) and Python 3.11–3.14 test targets.
- Structured `RPCRequestError` diagnostics with RPC code, data, error, and response fields.

### Changed

- Python 3.11 is now the minimum supported runtime.
- `solders` is now a required dependency.
- QR generation moved behind the optional `solathon[qr]` extra; normal imports stay free of Pillow and qrcode startup cost.
- `PublicKey` is immutable, integer construction is a full 256-bit big-endian conversion, and PDA/seed derivation delegates to canonical native primitives.
- `Keypair` consistently uses Ed25519 material and validates the public half of 64-byte keypairs.
- Private-key string and repr output is redacted; secret export now requires an explicit bytes or base58 operation.
- Legacy transaction compilation now derives canonical account order and signer metadata, binds signatures to signer keys, and applies Solana's packet-size rules.
- Sync and async clients now share the same public method names and parameter shapes.
- Raw transaction submission and simulation use base64 consistently.
- Simulations with `sig_verify=False` can serialize intentionally unsigned transactions without weakening signed submissions.
- SOL and token amount conversion rejects fractional base units, non-finite numbers, negative values, and unsigned 64-bit overflow instead of truncating.
- Solana Pay amounts are encoded as fixed-point decimal text and parsed as `Decimal`; recipients and references are typed as `PublicKey` values, with ordered multiple references retained.
- Solana Pay transaction-request endpoints must use absolute HTTPS URLs, and returned transactions are size-, format-, signer-, and signature-validated; requests that expect any signer other than the requested account are rejected.
- Root-package and Solana Pay exports are loaded lazily.

### Fixed

- Fee-payer placement, duplicate account merging, readonly counts, required-signature counts, empty instruction handling, and partial-signature behavior in legacy transactions.
- Transaction deserialization and signature verification against the exact serialized message.
- Async token-owner queries that previously referenced an undefined commitment variable.
- Recursive JSON-RPC serialization of nested public keys and bytes, correct empty parameter arrays, response-envelope preservation, and stable batch ordering.
- Block and transaction response parsing for null values, binary encodings, inner instructions, loaded addresses, return data, and v1 `transactionConfig` metadata.
- Solana Pay URL escaping, zero amounts, decimal precision, transaction-response base64 decoding, signer checks, reference pagination, memo placement, and native-transfer validation.
- Solana Pay transaction fetches use an isolated HTTP transport so RPC-provider credentials and cookies cannot leak to a merchant origin.
- The transfer example is dry-run by default and prints an unsigned wire template, avoiding accidental secret generation or transaction submission during exploration.
- Classic Associated Token Account creation uses its legacy empty instruction data and Rent sysvar account; idempotent creation uses the modern six-account variant.
- Alternate `getBlock` transaction detail shapes pass through intact instead of being forced through the full-transaction response model.
- QR rendering without global working-directory changes or leaked image resources.

### Compatibility notes

- RPC transaction readers default to `max_supported_transaction_version=0`. Set `1` only in consumers intentionally prepared for experimental v1 responses.
- V1 requires positive compute-unit and loaded-account-data limits in `TransactionConfig`; its priority fee is total lamports. Compute Budget instructions are rejected for v1 because the runtime treats them as no-ops.
- Generic Token-2022 transfers reject transfer-fee, transfer-hook, non-transferable, and unknown future extensions when their semantics cannot be applied safely. Specialized extension instruction construction is not included yet.
- Solana Pay Token-2022 creation fails closed for transfer-fee, transfer-hook, transformed-UI-amount, non-transferable, paused, and unknown extensions; required incoming memos are honored when supplied.

## [1.2.0]

- Last 1.x release. Supported the core JSON-RPC clients, legacy transactions, System and Compute Budget instructions, and initial Solana Pay helpers.

[2.0.0]: https://github.com/GitBolt/solathon/compare/v1.2.0...master
[1.2.0]: https://github.com/GitBolt/solathon/releases/tag/v1.2.0
