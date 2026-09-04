from __future__ import annotations

import base64
import json
import struct
import subprocess
import sys
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from solders.hash import Hash
from solders.instruction import CompiledInstruction as SoldersCompiledInstruction
from solders.message import Message as SoldersMessage
from solders.message import MessageHeader as SoldersMessageHeader
from solders.message import MessageV0 as SoldersMessageV0
from solders.message import MessageV1 as SoldersMessageV1
from solders.message import TransactionConfig as SoldersTransactionConfig
from solders.signature import Signature as SoldersSignature
from solders.transaction import Transaction as SoldersTransaction
from solders.transaction import VersionedTransaction as SoldersVersionedTransaction

from solathon.core.instructions import (
    MEMO_PROGRAM_ID,
    AccountMeta,
    Instruction,
    transfer,
)
from solathon.core.layouts import SYSTEM_PROGRAM_ID
from solathon.core.types import TransactionSignature
from solathon.core.types.account_info import AccountInfo
from solathon.core.types.block import BlockHash
from solathon.keypair import Keypair
from solathon.publickey import PublicKey
from solathon.solana_pay.create_qr import create_qr
from solathon.solana_pay.create_transfer import create_transfer
from solathon.solana_pay.encode_url import encode_url
from solathon.solana_pay.fetch_transaction import (
    MAX_JSON_RESPONSE_BYTES,
    _http_transport,
    fetch_transaction,
)
from solathon.solana_pay.find_reference import find_reference
from solathon.solana_pay.parse_url import parse_url
from solathon.solana_pay.types import TransactionRequestURL, TransferRequestURL
from solathon.solana_pay.validate_transfer import validate_transfer
from solathon.token import (
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    TokenExtensionType,
    UnsupportedTokenExtensionError,
    get_associated_token_address,
    transfer_checked,
)
from solathon.transaction import Transaction
from solathon.versioned import (
    MessageV0,
    MessageV1,
    TransactionConfig,
    VersionedTransaction,
)


def public_key(start: int) -> PublicKey:
    return PublicKey(bytes((start + index) % 256 for index in range(32)))


def keypair(start: int) -> Keypair:
    return Keypair(bytes((start + index) % 256 for index in range(32)))


def blockhash(start: int) -> str:
    return str(public_key(start))


def zero_payer_transaction_wire(
    account: PublicKey,
    recipient: PublicKey,
    recent_blockhash: str,
    version: int | None,
) -> bytes:
    """Build the temporarily unsanitized zero-payer form allowed by Pay."""

    header = SoldersMessageHeader(2, 0, 0)
    keys = [
        PublicKey(0).to_solders(),
        account.to_solders(),
        recipient.to_solders(),
    ]
    instruction = SoldersCompiledInstruction(
        0,
        b"\x02\x00\x00\x00" + (1).to_bytes(8, "little"),
        bytes([1, 2]),
    )
    native_hash = Hash.from_string(recent_blockhash)
    signatures = [SoldersSignature.default(), SoldersSignature.default()]
    if version is None:
        message = SoldersMessage.new_with_compiled_instructions(
            2, 0, 0, keys, native_hash, [instruction]
        )
        return bytes(SoldersTransaction.populate(message, signatures))
    if version == 0:
        versioned_message = SoldersMessageV0(
            header, keys, native_hash, [instruction], []
        )
    else:
        versioned_message = SoldersMessageV1(
            header,
            SoldersTransactionConfig(
                compute_unit_limit=200_000,
                loaded_accounts_data_size_limit=64_000,
            ),
            native_hash,
            keys,
            [instruction],
        )
    return bytes(SoldersVersionedTransaction.populate(versioned_message, signatures))


class TransferClient:
    def __init__(self, sender: PublicKey, lamports: int = 10_000_000_000):
        self.sender = sender
        self.lookups: list[list[PublicKey]] = []
        self.info = AccountInfo(
            {
                "lamports": lamports,
                "owner": str(SYSTEM_PROGRAM_ID),
                "executable": False,
                "rentEpoch": 0,
                "data": ["", "base64"],
            }
        )

    def get_multiple_accounts(self, addresses, commitment=None, encoding="base64"):
        self.lookups.append(addresses)
        assert encoding == "base64"
        return [self.info if address == self.sender else None for address in addresses]

    def get_latest_blockhash(self, commitment=None):
        return BlockHash({"blockhash": blockhash(100), "lastValidBlockHeight": 10_000})


def test_solana_pay_package_does_not_import_qr_dependencies() -> None:
    code = """
import sys
import solathon.solana_pay
assert 'qrcode' not in sys.modules
assert 'PIL' not in sys.modules
from solathon.solana_pay import encode_url
assert callable(encode_url)
assert 'qrcode' not in sys.modules
assert 'PIL' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_create_qr_returns_a_rewound_png_when_extra_is_installed() -> None:
    pytest.importorskip("qrcode")
    image = create_qr("solana:https://example.com/pay")
    assert image.tell() == 0
    assert image.read(8) == b"\x89PNG\r\n\x1a\n"


def test_transfer_url_fixed_decimal_and_ordered_references() -> None:
    recipient, mint, first, second = (
        public_key(1),
        public_key(2),
        public_key(3),
        public_key(4),
    )
    url = encode_url(
        recipient=recipient,
        amount=Decimal("1E-7"),
        spl_token=mint,
        reference=[first, second, first],
        label="Coffee shop",
        memo="order/123",
    )

    assert "amount=0.0000001" in url
    assert "amount=1E" not in url
    assert "Coffee%20shop" in url
    parsed = parse_url(url)
    assert isinstance(parsed, TransferRequestURL)
    assert parsed.recipient == recipient
    assert parsed.amount == Decimal("0.0000001")
    assert parsed.spl_token == mint
    assert parsed.reference == [first, second, first]
    assert parsed.memo == "order/123"


def test_zero_is_valid_but_amount_grammar_is_strict() -> None:
    recipient = public_key(5)
    url = encode_url(recipient=recipient, amount=0)
    assert url.endswith("?amount=0")
    parsed = parse_url(url)
    assert isinstance(parsed, TransferRequestURL)
    assert parsed.amount == Decimal(0)

    for invalid in [".1", "1.", "1e-3", "+1", "-0", "NaN", "Infinity"]:
        with pytest.raises(ValueError, match="amount"):
            parse_url(f"solana:{recipient}?amount={invalid}")
    with pytest.raises(ValueError, match="9 decimal"):
        encode_url(recipient=recipient, amount="0.0000000001")
    with pytest.raises(ValueError, match="only appear once"):
        parse_url(f"solana:{recipient}?amount=1&amount=2")


def test_transaction_link_is_encoded_only_when_its_query_needs_it() -> None:
    plain = encode_url(link="https://example.com/pay")
    assert plain == "solana:https://example.com/pay"

    encoded = encode_url(
        link="https://example.com/pay?order=123",
        label="Store",
        message="Confirm payment",
    )
    assert encoded.startswith("solana:https%3A%2F%2Fexample.com%2Fpay%3Forder%3D123?")
    parsed = parse_url(encoded)
    assert isinstance(parsed, TransactionRequestURL)
    assert parsed.link == "https://example.com/pay?order=123"
    assert parsed.label == "Store"
    assert parsed.message == "Confirm payment"

    with pytest.raises(ValueError, match="credentials"):
        encode_url(link="https://user:secret@example.com/pay")
    with pytest.raises(ValueError, match="fragments"):
        encode_url(link="https://example.com/pay#fragment")
    with pytest.raises(ValueError, match="percent"):
        parse_url(f"solana:{public_key(6)}?label=%ZZ")
    with pytest.raises(ValueError, match="amount"):
        parse_url(f"solana:{public_key(6)}?amount=\u0661.\u0665")

    escaped_path = "https://example.com/orders/%2Fspecial"
    assert parse_url(encode_url(link=escaped_path)).link == escaped_path


def test_find_reference_paginates_to_oldest_within_rpc_window() -> None:
    calls = []
    pages = {
        "start": [
            {"signature": "new", "slot": 3},
            {"signature": "middle", "slot": 2},
        ],
        "middle": [{"signature": "old", "slot": 1}],
    }

    class Client:
        def get_signatures_for_address(self, address, **options):
            calls.append((address, options))
            return [TransactionSignature(item) for item in pages[options["before"]]]

    found = find_reference(
        Client(),
        public_key(7),
        limit=2,
        before="start",
        until="floor",
        commitment="confirmed",
    )
    assert found.signature == "old"
    assert [options["before"] for _, options in calls] == ["start", "middle"]
    assert all(options["until"] == "floor" for _, options in calls)


def test_create_native_transfer_places_memo_before_final_transfer() -> None:
    sender = keypair(7)
    recipient, first, second = public_key(8), public_key(9), public_key(10)
    client = TransferClient(sender.public_key)
    transaction = create_transfer(
        client,
        sender,
        {
            "recipient": recipient,
            "amount": Decimal("0.25"),
            "reference": [first, second],
            "memo": "invoice 42",
        },
    )

    assert client.lookups == [[sender.public_key, recipient]]
    assert transaction.instructions[-2].program_id == MEMO_PROGRAM_ID
    assert transaction.instructions[-2].data == b"invoice 42"
    assert transaction.instructions[-2].keys == [
        AccountMeta(sender.public_key, True, False)
    ]
    payment = transaction.instructions[-1]
    assert payment.program_id == SYSTEM_PROGRAM_ID
    assert [meta.public_key for meta in payment.keys[2:]] == [first, second]
    assert all(not meta.is_signer and not meta.is_writable for meta in payment.keys[2:])
    assert transaction.recent_blockhash == blockhash(100)


def account_info(owner: PublicKey, data: bytes, lamports: int = 1) -> AccountInfo:
    return AccountInfo(
        {
            "lamports": lamports,
            "owner": str(owner),
            "executable": False,
            "rentEpoch": 0,
            "data": [base64.b64encode(data).decode("ascii"), "base64"],
        }
    )


def mint_data(decimals: int) -> bytes:
    return (
        bytes(36)
        + (10_000_000).to_bytes(8, "little")
        + bytes([decimals, 1])
        + bytes(36)
    )


def token_account_data(mint: PublicKey, owner: PublicKey, amount: int) -> bytes:
    return b"".join(
        [
            bytes(mint),
            bytes(owner),
            amount.to_bytes(8, "little"),
            bytes(36),
            b"\x01",
            bytes(12),
            bytes(8),
            bytes(36),
        ]
    )


def token_2022_state(
    base: bytes,
    account_type: int,
    extensions: list[tuple[int, bytes]],
) -> bytes:
    assert len(base) <= 165
    return b"".join(
        [
            base,
            bytes(165 - len(base)),
            bytes([account_type]),
            *(
                extension_type.to_bytes(2, "little")
                + len(data).to_bytes(2, "little")
                + data
                for extension_type, data in extensions
            ),
        ]
    )


@pytest.mark.parametrize("token_program", [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID])
def test_create_token_transfer_uses_program_aware_atas_and_checked_amount(
    token_program: PublicKey,
) -> None:
    sender = keypair(40)
    recipient, mint, reference = public_key(41), public_key(42), public_key(43)
    sender_ata = get_associated_token_address(sender.public_key, mint, token_program)
    recipient_ata = get_associated_token_address(recipient, mint, token_program)
    accounts = {
        mint: account_info(token_program, mint_data(6)),
        sender_ata: account_info(
            token_program,
            token_account_data(mint, sender.public_key, 2_000_000),
        ),
        recipient_ata: account_info(
            token_program,
            token_account_data(mint, recipient, 10),
        ),
    }

    class Client:
        def get_account_info(self, address, commitment=None):
            return accounts[address]

        def get_multiple_accounts(self, addresses, commitment=None, encoding="base64"):
            assert encoding == "base64"
            return [accounts.get(address) for address in addresses]

        def get_latest_blockhash(self, commitment=None):
            return BlockHash(
                {"blockhash": blockhash(140), "lastValidBlockHeight": 10_000}
            )

    transaction = create_transfer(
        Client(),
        sender,
        {
            "recipient": recipient,
            "amount": Decimal("1.25"),
            "spl_token": mint,
            "reference": reference,
            "memo": "token order",
        },
    )

    instruction = transaction.instructions[-1]
    assert instruction.program_id == token_program
    assert [meta.public_key for meta in instruction.keys[:4]] == [
        sender_ata,
        mint,
        recipient_ata,
        sender.public_key,
    ]
    assert instruction.keys[-1] == AccountMeta(reference, False, False)
    assert instruction.data == b"\x0c" + (1_250_000).to_bytes(8, "little") + b"\x06"


@pytest.mark.parametrize(
    ("extension_type", "extension_data", "message"),
    [
        (TokenExtensionType.NON_TRANSFERABLE, b"", "non-transferable"),
        (
            TokenExtensionType.INTEREST_BEARING_CONFIG,
            bytes(52),
            "timestamp-aware",
        ),
        (
            TokenExtensionType.SCALED_UI_AMOUNT,
            bytes(32) + struct.pack("<dqd", 0.5, 0, 0.5),
            "multiplier-aware",
        ),
        (TokenExtensionType.PAUSABLE, bytes(32) + b"\x01", "paused"),
        (65_535, b"", "unknown Token-2022 extension"),
    ],
)
def test_create_token_transfer_rejects_unsafe_or_unknown_mint_extensions(
    extension_type: int,
    extension_data: bytes,
    message: str,
) -> None:
    sender = keypair(44)
    recipient, mint = public_key(45), public_key(46)
    sender_ata = get_associated_token_address(
        sender.public_key, mint, TOKEN_2022_PROGRAM_ID
    )
    recipient_ata = get_associated_token_address(recipient, mint, TOKEN_2022_PROGRAM_ID)
    accounts = {
        mint: account_info(
            TOKEN_2022_PROGRAM_ID,
            token_2022_state(
                mint_data(6),
                1,
                [(int(extension_type), extension_data)],
            ),
        ),
        sender_ata: account_info(
            TOKEN_2022_PROGRAM_ID,
            token_account_data(mint, sender.public_key, 2_000_000),
        ),
        recipient_ata: account_info(
            TOKEN_2022_PROGRAM_ID,
            token_account_data(mint, recipient, 0),
        ),
    }

    class Client:
        def get_account_info(self, address, commitment=None):
            return accounts[address]

        def get_multiple_accounts(self, addresses, commitment=None, encoding="base64"):
            return [accounts.get(address) for address in addresses]

        def get_latest_blockhash(self, commitment=None):
            return BlockHash(
                {"blockhash": blockhash(145), "lastValidBlockHeight": 10_000}
            )

    with pytest.raises(UnsupportedTokenExtensionError, match=message):
        create_transfer(
            Client(),
            sender,
            {
                "recipient": recipient,
                "amount": Decimal("1"),
                "spl_token": mint,
            },
        )


def test_create_token_transfer_honors_required_memo_extension() -> None:
    sender = keypair(47)
    recipient, mint = public_key(48), public_key(49)
    sender_ata = get_associated_token_address(
        sender.public_key, mint, TOKEN_2022_PROGRAM_ID
    )
    recipient_ata = get_associated_token_address(recipient, mint, TOKEN_2022_PROGRAM_ID)
    accounts = {
        mint: account_info(TOKEN_2022_PROGRAM_ID, mint_data(6)),
        sender_ata: account_info(
            TOKEN_2022_PROGRAM_ID,
            token_account_data(mint, sender.public_key, 2_000_000),
        ),
        recipient_ata: account_info(
            TOKEN_2022_PROGRAM_ID,
            token_2022_state(
                token_account_data(mint, recipient, 0),
                2,
                [(int(TokenExtensionType.MEMO_TRANSFER), b"\x01")],
            ),
        ),
    }

    class Client:
        def get_account_info(self, address, commitment=None):
            return accounts[address]

        def get_multiple_accounts(self, addresses, commitment=None, encoding="base64"):
            return [accounts.get(address) for address in addresses]

        def get_latest_blockhash(self, commitment=None):
            return BlockHash(
                {"blockhash": blockhash(146), "lastValidBlockHeight": 10_000}
            )

    fields = {
        "recipient": recipient,
        "amount": Decimal("1"),
        "spl_token": mint,
    }
    with pytest.raises(
        UnsupportedTokenExtensionError, match="requires a transfer memo"
    ):
        create_transfer(Client(), sender, fields)

    transaction = create_transfer(Client(), sender, {**fields, "memo": "invoice"})
    assert transaction.instructions[-2].program_id == MEMO_PROGRAM_ID
    assert transaction.instructions[-2].data == b"invoice"


def transaction_response(
    transaction: Transaction,
    recipient: PublicKey,
    received_lamports: int,
):
    message = transaction._message_and_signatures()
    recipient_index = message.account_keys.index(recipient)
    pre_balances = [0] * len(message.account_keys)
    post_balances = pre_balances.copy()
    post_balances[recipient_index] = received_lamports
    meta = SimpleNamespace(
        err=None,
        loaded_writable_addresses=[],
        loaded_readonly_addresses=[],
        pre_balances=pre_balances,
        post_balances=post_balances,
    )
    return SimpleNamespace(
        meta=meta,
        transaction=SimpleNamespace(message=message, signatures=[]),
    )


def test_validate_native_transfer_checks_final_instruction_memo_and_net_amount() -> (
    None
):
    sender = keypair(11)
    recipient, reference = public_key(12), public_key(13)
    amount = 250_000_000
    payment = transfer(sender.public_key, recipient, amount)
    payment.keys.append(AccountMeta(reference, False, False))
    memo = Instruction([], MEMO_PROGRAM_ID, b"invoice")
    transaction = Transaction(
        fee_payer=sender.public_key,
        signers=[sender],
        recent_blockhash=blockhash(110),
        instructions=[memo, payment],
    )
    response = transaction_response(transaction, recipient, amount)

    class Client:
        def get_transaction(self, signature, **kwargs):
            assert signature == "signature"
            assert kwargs["max_supported_transaction_version"] == 0
            return response

    assert (
        validate_transfer(
            Client(),
            "signature",
            {
                "recipient": recipient,
                "amount": Decimal("0.25"),
                "reference": reference,
                "memo": "invoice",
            },
        )
        is response
    )

    response.meta.post_balances[
        response.transaction.message.account_keys.index(recipient)
    ] -= 1
    with pytest.raises(ValueError, match="did not receive"):
        validate_transfer(
            Client(),
            "signature",
            {
                "recipient": recipient,
                "amount": Decimal("0.25"),
                "reference": reference,
                "memo": "invoice",
            },
        )


@pytest.mark.parametrize("token_program", [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID])
def test_validate_token_transfer_checks_ata_mint_amount_and_balance(
    token_program: PublicKey,
) -> None:
    sender = keypair(50)
    recipient, mint, reference = public_key(51), public_key(52), public_key(53)
    sender_ata = get_associated_token_address(sender.public_key, mint, token_program)
    recipient_ata = get_associated_token_address(recipient, mint, token_program)
    payment = transfer_checked(
        sender_ata,
        mint,
        recipient_ata,
        sender.public_key,
        1_250_000,
        6,
        token_program_id=token_program,
    )
    payment.keys.append(AccountMeta(reference, False, False))
    memo = Instruction(
        [AccountMeta(sender.public_key, True, False)], MEMO_PROGRAM_ID, b"token order"
    )
    transaction = Transaction(
        fee_payer=sender.public_key,
        signers=[sender],
        recent_blockhash=blockhash(150),
        instructions=[memo, payment],
    )
    message = transaction._message_and_signatures()
    recipient_index = message.account_keys.index(recipient_ata)
    meta = SimpleNamespace(
        err=None,
        loaded_writable_addresses=[],
        loaded_readonly_addresses=[],
        pre_balances=[0] * len(message.account_keys),
        post_balances=[0] * len(message.account_keys),
        pre_token_balances=[
            {
                "accountIndex": recipient_index,
                "mint": str(mint),
                "owner": str(recipient),
                "programId": str(token_program),
                "uiTokenAmount": {"amount": "10", "decimals": 6},
            }
        ],
        post_token_balances=[
            {
                "accountIndex": recipient_index,
                "mint": str(mint),
                "owner": str(recipient),
                "programId": str(token_program),
                "uiTokenAmount": {"amount": "1250010", "decimals": 6},
            }
        ],
    )
    response = SimpleNamespace(
        meta=meta,
        transaction=SimpleNamespace(message=message, signatures=[]),
    )

    class Client:
        def get_transaction(self, signature, **kwargs):
            assert kwargs["commitment"] == "confirmed"
            return response

        def get_account_info(self, address, commitment=None):
            assert token_program == TOKEN_2022_PROGRAM_ID
            assert address == mint
            return account_info(token_program, mint_data(6))

    fields = {
        "recipient": recipient,
        "amount": Decimal("1.25"),
        "spl_token": mint,
        "reference": reference,
        "memo": "token order",
    }
    assert validate_transfer(Client(), "signature", fields) is response

    meta.post_token_balances[0]["uiTokenAmount"]["amount"] = "1250009"
    with pytest.raises(ValueError, match="requested token amount"):
        validate_transfer(Client(), "signature", fields)


def test_validate_token_2022_rejects_nonstandard_ui_amount_semantics() -> None:
    sender = keypair(54)
    recipient, mint = public_key(55), public_key(56)
    sender_ata = get_associated_token_address(
        sender.public_key, mint, TOKEN_2022_PROGRAM_ID
    )
    recipient_ata = get_associated_token_address(recipient, mint, TOKEN_2022_PROGRAM_ID)
    payment = transfer_checked(
        sender_ata,
        mint,
        recipient_ata,
        sender.public_key,
        1,
        0,
        token_program_id=TOKEN_2022_PROGRAM_ID,
    )
    transaction = Transaction(
        fee_payer=sender.public_key,
        signers=[sender],
        recent_blockhash=blockhash(155),
        instructions=[payment],
    )
    message = transaction._message_and_signatures()
    recipient_index = message.account_keys.index(recipient_ata)
    meta = SimpleNamespace(
        err=None,
        loaded_writable_addresses=[],
        loaded_readonly_addresses=[],
        pre_balances=[0] * len(message.account_keys),
        post_balances=[0] * len(message.account_keys),
        pre_token_balances=[
            {
                "accountIndex": recipient_index,
                "mint": str(mint),
                "owner": str(recipient),
                "programId": str(TOKEN_2022_PROGRAM_ID),
                "uiTokenAmount": {"amount": "0", "decimals": 0},
            }
        ],
        post_token_balances=[
            {
                "accountIndex": recipient_index,
                "mint": str(mint),
                "owner": str(recipient),
                "programId": str(TOKEN_2022_PROGRAM_ID),
                "uiTokenAmount": {"amount": "1", "decimals": 0},
            }
        ],
    )
    response = SimpleNamespace(
        meta=meta,
        transaction=SimpleNamespace(message=message, signatures=[]),
    )
    scaled_mint = token_2022_state(
        mint_data(0),
        1,
        [
            (
                int(TokenExtensionType.SCALED_UI_AMOUNT),
                bytes(32) + struct.pack("<dqd", 0.5, 0, 0.5),
            )
        ],
    )

    class Client:
        def get_transaction(self, signature, **kwargs):
            return response

        def get_account_info(self, address, commitment=None):
            assert address == mint
            return account_info(TOKEN_2022_PROGRAM_ID, scaled_mint)

    # A multiplier of 0.5 means a 1-UI-token request needs two raw units.
    # Transaction metadata records raw balances, so decimals-only validation
    # would incorrectly accept this one-unit transfer.
    with pytest.raises(UnsupportedTokenExtensionError, match="multiplier-aware"):
        validate_transfer(
            Client(),
            "signature",
            {
                "recipient": recipient,
                "amount": Decimal("1"),
                "spl_token": mint,
            },
        )


def test_validate_token_balance_owner_and_program_index_are_strict() -> None:
    sender = keypair(57)
    recipient, mint = public_key(58), public_key(59)
    sender_ata = get_associated_token_address(sender.public_key, mint)
    recipient_ata = get_associated_token_address(recipient, mint)
    payment = transfer_checked(
        sender_ata,
        mint,
        recipient_ata,
        sender.public_key,
        1,
        0,
    )
    transaction = Transaction(
        fee_payer=sender.public_key,
        signers=[sender],
        recent_blockhash=blockhash(156),
        instructions=[payment],
    )
    message = transaction._message_and_signatures()
    recipient_index = message.account_keys.index(recipient_ata)
    meta = SimpleNamespace(
        err=None,
        loaded_writable_addresses=[],
        loaded_readonly_addresses=[],
        pre_balances=[0] * len(message.account_keys),
        post_balances=[0] * len(message.account_keys),
        pre_token_balances=[
            {
                "accountIndex": recipient_index,
                "mint": str(mint),
                "owner": str(public_key(60)),
                "programId": str(TOKEN_PROGRAM_ID),
                "uiTokenAmount": {"amount": "0", "decimals": 0},
            }
        ],
        post_token_balances=[
            {
                "accountIndex": recipient_index,
                "mint": str(mint),
                "owner": str(public_key(60)),
                "programId": str(TOKEN_PROGRAM_ID),
                "uiTokenAmount": {"amount": "1", "decimals": 0},
            }
        ],
    )
    response = SimpleNamespace(
        meta=meta,
        transaction=SimpleNamespace(message=message, signatures=[]),
    )

    class Client:
        def get_transaction(self, signature, **kwargs):
            return response

    fields = {"recipient": recipient, "amount": Decimal("1"), "spl_token": mint}
    with pytest.raises(ValueError, match="wrong owner"):
        validate_transfer(Client(), "signature", fields)

    malformed = SimpleNamespace(
        accounts=list(message.instructions[-1].accounts),
        data=message.instructions[-1].data,
        program_id_index=None,
    )
    message.instructions[-1] = malformed
    with pytest.raises(ValueError, match="invalid program index"):
        validate_transfer(Client(), "signature", fields)


class FetchClient:
    def __init__(self, latest: str):
        self.latest = latest
        self.calls = 0

    def get_latest_blockhash(self, commitment=None):
        self.calls += 1
        return BlockHash({"blockhash": self.latest, "lastValidBlockHeight": 500})


def test_fetch_transaction_does_not_reuse_authenticated_rpc_transport() -> None:
    rpc_http = httpx.Client(headers={"Authorization": "Bearer rpc-secret"})
    rpc_client = SimpleNamespace(http=SimpleNamespace(client=rpc_http, timeout=7.0))

    transport, owns_transport = _http_transport(rpc_client, None)
    try:
        assert owns_transport
        assert transport is not rpc_http
        assert "authorization" not in transport.headers
    finally:
        transport.close()
        rpc_http.close()


def mock_transaction_server(wire: bytes):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["accept"] == "application/json"
        body = json.loads(request.content)
        assert isinstance(body["account"], str)
        return httpx.Response(
            200,
            json={"transaction": base64.b64encode(wire).decode("ascii")},
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_transaction_stops_oversized_response_while_streaming() -> None:
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b"x" * (MAX_JSON_RESPONSE_BYTES + 1),
            )
        )
    )
    with http, pytest.raises(ValueError, match="too large"):
        fetch_transaction(
            FetchClient(blockhash(120)),
            public_key(14),
            "https://example.com/pay",
            http_client=http,
        )


def test_fetch_transaction_refreshes_safe_unsigned_legacy_template() -> None:
    signer = keypair(14)
    recipient = public_key(15)
    transaction = Transaction(
        fee_payer=signer.public_key,
        signers=[signer.public_key],
        recent_blockhash=blockhash(120),
        instructions=[transfer(signer.public_key, recipient, 1)],
    )
    wire = transaction.serialize(
        require_all_signatures=False,
        verify_signatures=False,
    )
    client = FetchClient(blockhash(121))
    with mock_transaction_server(wire) as http:
        fetched = fetch_transaction(
            client,
            signer.public_key,
            "https://example.com/pay",
            http_client=http,
        )

    assert isinstance(fetched, Transaction)
    assert fetched.recent_blockhash == blockhash(121)
    assert client.calls == 1
    assert [pair.public_key for pair in fetched.signatures] == [signer.public_key]


def test_fetch_transaction_merges_zero_payer_with_requested_legacy_signer() -> None:
    account = keypair(60)
    wire = zero_payer_transaction_wire(
        account.public_key,
        public_key(61),
        blockhash(160),
        None,
    )
    client = FetchClient(blockhash(161))

    with mock_transaction_server(wire) as http:
        fetched = fetch_transaction(
            client,
            account.public_key,
            "https://example.com/pay",
            http_client=http,
        )

    assert isinstance(fetched, Transaction)
    assert fetched.fee_payer == account.public_key
    assert [pair.public_key for pair in fetched.signatures] == [account.public_key]
    assert fetched.recent_blockhash == blockhash(161)


@pytest.mark.parametrize("version", [0, 1])
def test_fetch_transaction_merges_zero_payer_with_versioned_signer(
    version: int,
) -> None:
    account = keypair(62)
    wire = zero_payer_transaction_wire(
        account.public_key,
        public_key(63),
        blockhash(162),
        version,
    )
    client = FetchClient(blockhash(163))

    with mock_transaction_server(wire) as http:
        fetched = fetch_transaction(
            client,
            account.public_key,
            "https://example.com/pay",
            http_client=http,
        )

    assert isinstance(fetched, VersionedTransaction)
    assert fetched.message.account_keys[0] == account.public_key
    assert fetched.message.account_keys.count(account.public_key) == 1
    assert fetched.message.header.num_required_signatures == 1
    assert len(fetched.signatures) == 1
    assert fetched.verify_present_signatures()


def test_fetch_transaction_rejects_a_fully_signed_unrelated_transaction() -> None:
    merchant = keypair(64)
    transaction = Transaction(
        fee_payer=merchant.public_key,
        signers=[merchant],
        recent_blockhash=blockhash(164),
        instructions=[transfer(merchant.public_key, public_key(65), 1)],
    )
    transaction.sign()
    client = FetchClient(blockhash(165))
    with mock_transaction_server(transaction.serialize()) as http:
        with pytest.raises(ValueError, match="unauthorized signer"):
            fetch_transaction(
                client,
                public_key(66),
                "https://example.com/pay",
                http_client=http,
            )

    assert client.calls == 0


@pytest.mark.parametrize("version", [0, 1])
def test_fetch_transaction_understands_unsigned_v0_and_v1_wire_layouts(
    version: int,
) -> None:
    signer = keypair(15)
    instruction = transfer(signer.public_key, public_key(16), 1)
    old_hash = Hash.from_string(blockhash(126))
    if version == 0:
        message = MessageV0.compile(signer.public_key, [instruction], old_hash)
    else:
        message = MessageV1.compile(
            signer.public_key,
            [instruction],
            old_hash,
            TransactionConfig(
                compute_unit_limit=200_000,
                loaded_accounts_data_size_limit=64_000,
            ),
        )
    wire = VersionedTransaction(message).serialize(require_all_signatures=False)
    latest = blockhash(127)
    client = FetchClient(latest)

    with mock_transaction_server(wire) as http:
        fetched = fetch_transaction(
            client,
            signer.public_key,
            "https://example.com/pay",
            http_client=http,
        )

    assert isinstance(fetched, VersionedTransaction)
    assert fetched.version == version
    assert fetched.recent_blockhash == latest
    assert fetched.verify_present_signatures()


@pytest.mark.parametrize("cosigner_signed", [False, True])
def test_fetch_transaction_rejects_any_non_requested_required_signer(
    cosigner_signed: bool,
) -> None:
    account, cosigner = keypair(16), keypair(17)
    recipient = public_key(18)
    instruction = transfer(account.public_key, recipient, 1)
    instruction.keys.append(AccountMeta(cosigner.public_key, True, False))
    transaction = Transaction(
        fee_payer=account.public_key,
        signers=[
            account.public_key,
            cosigner if cosigner_signed else cosigner.public_key,
        ],
        recent_blockhash=blockhash(122),
        instructions=[instruction],
    )
    if cosigner_signed:
        transaction.sign()
    wire = transaction.serialize(False, False)
    with mock_transaction_server(wire) as http:
        with pytest.raises(ValueError, match="unauthorized signer"):
            fetch_transaction(
                FetchClient(blockhash(123)),
                account.public_key,
                "https://example.com/pay",
                http_client=http,
            )


def test_fetch_transaction_rejects_invalid_requested_account_signature() -> None:
    account = keypair(19)
    instruction = transfer(account.public_key, public_key(21), 1)
    transaction = Transaction(
        fee_payer=account.public_key,
        signers=[account],
        recent_blockhash=blockhash(124),
        instructions=[instruction],
    )
    transaction.sign()
    wire = bytearray(transaction.serialize(False, False))
    wire[1] ^= 1  # signature count byte, then the requested account signature

    with mock_transaction_server(bytes(wire)) as http:
        with pytest.raises(ValueError, match="invalid signature"):
            fetch_transaction(
                FetchClient(blockhash(125)),
                account.public_key,
                "https://example.com/pay",
                http_client=http,
            )
