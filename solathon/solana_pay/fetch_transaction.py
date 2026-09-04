from __future__ import annotations

import base64
import binascii
import json
from typing import Any
from urllib.parse import urlsplit

import httpx
from base58 import b58decode
from solders.transaction import Transaction as SoldersTransaction

from ..client import Client
from ..core.instructions import AccountMeta, Instruction
from ..core.message import Message, decode_length
from ..core.types import Commitment
from ..core.types.block import BlockHash
from ..publickey import PublicKey
from ..transaction import DEFAULT_SIGNATURE, PACKET_DATA_SIZE, Transaction
from ..utils import unwrap_rpc_response
from ..versioned import MessageV0, MessageV1, VersionedTransaction
from .encode_url import MAX_SOLANA_PAY_URL_LENGTH

MAX_TRANSACTION_RESPONSE_BYTES = 4096
MAX_JSON_RESPONSE_BYTES = 16 * 1024
ZERO_PUBLIC_KEY = PublicKey(0)


def fetch_transaction(
    client: Client,
    account: PublicKey,
    link: str,
    commitment: Commitment | None = None,
    *,
    http_client: httpx.Client | None = None,
) -> Transaction | VersionedTransaction:
    """Fetch and validate an untrusted Solana Pay transaction response.

    The requested ``account`` must be the transaction's only required signer.
    A safe unsigned template gets the requested account as fee payer and a
    fresh blockhash. No transaction is signed by this function.
    """

    if not isinstance(account, PublicKey):
        raise TypeError("account must be a PublicKey")
    _validate_transaction_request_link(link)

    transport, owns_transport = _http_transport(client, http_client)
    try:
        with transport.stream(
            "POST",
            link,
            headers={
                "Accept": "application/json",
                "Cache-Control": "no-cache",
                "Content-Type": "application/json",
            },
            json={"account": str(account)},
            follow_redirects=False,
        ) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                if len(content) + len(chunk) > MAX_JSON_RESPONSE_BYTES:
                    raise ValueError("Transaction request response is too large")
                content.extend(chunk)
        try:
            payload = json.loads(content)
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError(
                "Transaction request response is not valid JSON"
            ) from error
    finally:
        if owns_transport:
            transport.close()

    if not isinstance(payload, dict):
        raise ValueError("Transaction request response must be a JSON object")
    encoded_transaction = payload.get("transaction")
    if not isinstance(encoded_transaction, str) or not encoded_transaction:
        raise ValueError("Transaction request response is missing a transaction")
    try:
        wire_transaction = base64.b64decode(encoded_transaction, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Transaction request returned invalid base64") from error
    if not wire_transaction:
        raise ValueError("Transaction request returned an empty transaction")
    if len(wire_transaction) > MAX_TRANSACTION_RESPONSE_BYTES:
        raise ValueError("Transaction request returned an oversized transaction")

    transaction = _deserialize_transaction(wire_transaction)
    required_signers, present = _signer_state(transaction)

    if not any(present):
        # The specification allows a zero fee payer in an unsigned template.
        # If its instructions also require ``account``, serialization contains
        # two signer entries which collapse after the wallet becomes payer.
        allowed_shapes = ([account], [ZERO_PUBLIC_KEY], [ZERO_PUBLIC_KEY, account])
        if required_signers not in allowed_shapes:
            raise ValueError("Unsigned transaction expects an unauthorized signer")
        if isinstance(transaction, Transaction):
            _initialize_unsigned_legacy(
                client, transaction, account, commitment, required_signers
            )
        else:
            _initialize_unsigned_versioned(
                client, transaction, account, commitment, required_signers
            )
        try:
            if isinstance(transaction, Transaction):
                transaction.serialize(
                    require_all_signatures=False,
                    verify_signatures=True,
                )
            else:
                transaction.serialize(require_all_signatures=False)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Transaction request could not be safely initialized"
            ) from error
        normalized_signers, normalized_present = _signer_state(transaction)
        if normalized_signers != [account] or any(normalized_present):
            raise ValueError("Unsigned transaction expects an unauthorized signer")
        return transaction

    if required_signers != [account]:
        raise ValueError("Transaction request expects an unauthorized signer")
    if not transaction.verify_present_signatures():
        raise ValueError("Transaction request returned an invalid signature")
    return transaction


def _deserialize_transaction(
    wire_transaction: bytes,
) -> Transaction | VersionedTransaction:
    # V1 transactions begin with their version byte and carry signatures at
    # the end. V0 and legacy transactions retain the leading signature vector.
    if wire_transaction[0] & 0x80:
        try:
            return VersionedTransaction._from_buffer(wire_transaction, sanitize=False)
        except (IndexError, TypeError, ValueError) as error:
            raise ValueError(
                "Transaction request returned a malformed versioned transaction"
            ) from error

    values = list(wire_transaction)
    try:
        signature_count = decode_length(values)
    except (IndexError, ValueError) as error:
        raise ValueError(
            "Transaction request returned a malformed signature count"
        ) from error
    if signature_count > 64:
        raise ValueError("Transaction request returned too many signatures")
    consumed = len(wire_transaction) - len(values)
    message_index = consumed + signature_count * 64
    if message_index >= len(wire_transaction):
        raise ValueError("Transaction request returned an incomplete transaction")
    try:
        if wire_transaction[message_index] & 0x80:
            return VersionedTransaction._from_buffer(wire_transaction, sanitize=False)
        if len(wire_transaction) > PACKET_DATA_SIZE:
            raise ValueError(
                f"Legacy transaction exceeds the {PACKET_DATA_SIZE}-byte limit"
            )
        return _legacy_transaction_from_buffer(wire_transaction)
    except Exception as error:
        raise ValueError(
            "Transaction request returned a malformed transaction"
        ) from error


def _legacy_transaction_from_buffer(wire_transaction: bytes) -> Transaction:
    """Parse legacy templates even when their temporary zero payer is invalid.

    A zero fee payer aliases the System Program address, so the intermediate
    message permitted by the Pay specification may fail runtime sanitization.
    It is accepted here only long enough to replace the payer, recompile, and
    sanitize the resulting transaction before it is returned.
    """

    try:
        return Transaction.from_buffer(wire_transaction)
    except Exception:
        native = SoldersTransaction.from_bytes(wire_transaction)
        return Transaction.populate(
            Message.from_solders(native.message),
            [bytes(signature) for signature in native.signatures],
        )


def _signer_state(
    transaction: Transaction | VersionedTransaction,
) -> tuple[list[PublicKey], list[bool]]:
    if isinstance(transaction, Transaction):
        required = [pair.public_key for pair in transaction.signatures]
        present = [pair.signature is not None for pair in transaction.signatures]
        return required, present

    required_count = transaction.message.header.num_required_signatures
    required = list(transaction.message.static_account_keys[:required_count])
    signatures = list(transaction.signatures)
    if len(signatures) != required_count:
        raise ValueError("Signature count does not match the versioned message")
    return required, [bytes(signature) != DEFAULT_SIGNATURE for signature in signatures]


def _initialize_unsigned_legacy(
    client: Client,
    transaction: Transaction,
    account: PublicKey,
    commitment: Commitment | None,
    required_signers: list[PublicKey],
) -> None:
    transaction.fee_payer = account
    if required_signers:
        transaction.signatures[0].public_key = account
    transaction.recent_blockhash = _latest_blockhash(client, commitment)


def _initialize_unsigned_versioned(
    client: Client,
    transaction: VersionedTransaction,
    account: PublicKey,
    commitment: Commitment | None,
    required_signers: list[PublicKey],
) -> None:
    if not required_signers:
        raise ValueError("Versioned transaction is missing a fee payer")
    if required_signers[0] == ZERO_PUBLIC_KEY:
        _replace_zero_fee_payer(transaction, account)
    transaction.message.recent_blockhash = _latest_blockhash(client, commitment)


def _replace_zero_fee_payer(
    transaction: VersionedTransaction,
    account: PublicKey,
) -> None:
    """Recompile a zero-payer message with ``account`` as canonical payer."""

    message = transaction.message
    if isinstance(message, MessageV0) and message.address_table_lookups:
        raise ValueError(
            "Cannot safely replace a zero fee payer in a lookup-table message"
        )
    instructions: list[Instruction] = []
    static_count = len(message.account_keys)
    for compiled in message.instructions:
        if compiled.program_id_index >= static_count or any(
            index >= static_count for index in compiled.accounts
        ):
            raise ValueError(
                "Cannot safely replace a zero fee payer with loaded instruction accounts"
            )
        instructions.append(
            Instruction(
                keys=[
                    AccountMeta(
                        message.account_keys[index],
                        message.is_account_signer(index),
                        message.is_account_writable(index),
                    )
                    for index in compiled.accounts
                ],
                program_id=message.account_keys[compiled.program_id_index],
                data=b58decode(compiled.data),
            )
        )

    replacement: MessageV0 | MessageV1
    if isinstance(message, MessageV0):
        replacement = MessageV0.compile(
            account,
            instructions,
            message.recent_blockhash,
        )
    elif isinstance(message, MessageV1):
        replacement = MessageV1.compile(
            account,
            instructions,
            message.recent_blockhash,
            message.config,
        )
    else:  # pragma: no cover - guarded by VersionedTransaction's constructor
        raise TypeError("Unsupported versioned message")
    transaction.message = replacement
    transaction.signatures = [
        DEFAULT_SIGNATURE for _ in range(replacement.header.num_required_signatures)
    ]


def _latest_blockhash(client: Client, commitment: Commitment | None) -> str:
    response: Any = client.get_latest_blockhash(commitment=commitment)
    if isinstance(response, BlockHash):
        return response.blockhash
    value = unwrap_rpc_response(response)
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    if not isinstance(value, dict):
        raise ValueError("Latest blockhash response is malformed")
    blockhash = value.get("blockhash")
    if not isinstance(blockhash, str):
        raise ValueError("Latest blockhash response is malformed")
    return blockhash


def _http_transport(
    client: Client,
    supplied: httpx.Client | None,
) -> tuple[httpx.Client, bool]:
    if supplied is not None:
        return supplied, False
    # Do not reuse the RPC transport for a cross-origin payment request. RPC
    # clients commonly carry provider API keys, cookies, or custom auth, and
    # HTTPX would merge those defaults into a request to the merchant's host.
    timeout = getattr(getattr(client, "http", None), "timeout", 30.0)
    return httpx.Client(timeout=timeout), True


def _validate_transaction_request_link(link: str) -> None:
    if not isinstance(link, str):
        raise TypeError("link must be a string")
    if len(link) > MAX_SOLANA_PAY_URL_LENGTH:
        raise ValueError(
            f"Transaction request link cannot exceed "
            f"{MAX_SOLANA_PAY_URL_LENGTH} characters"
        )
    if any(ord(character) < 0x20 or character.isspace() for character in link):
        raise ValueError("Transaction request link contains whitespace or controls")
    parsed = urlsplit(link)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Transaction request links must use absolute HTTPS URLs")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Transaction request links cannot contain credentials")
    if parsed.fragment:
        raise ValueError("Transaction request links cannot contain fragments")
    try:
        _ = parsed.port
    except ValueError as error:
        raise ValueError("Transaction request link has an invalid port") from error
