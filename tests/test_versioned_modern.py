from __future__ import annotations

import pytest
from solders.address_lookup_table_account import (
    AddressLookupTableAccount as SoldersAddressLookupTableAccount,
)
from solders.address_lookup_table_account import (
    LookupTableMeta,
)
from solders.hash import Hash
from solders.instruction import (
    AccountMeta as SoldersAccountMeta,
)
from solders.instruction import (
    CompiledInstruction as SoldersCompiledInstruction,
)
from solders.instruction import (
    Instruction as SoldersInstruction,
)
from solders.message import (
    MessageHeader as SoldersMessageHeader,
)
from solders.message import (
    MessageV0 as SoldersMessageV0,
)
from solders.message import (
    MessageV1 as SoldersMessageV1,
)
from solders.message import (
    TransactionConfig as SoldersTransactionConfig,
)
from solders.message import (
    to_bytes_versioned,
)
from solders.signature import Signature as SoldersSignature
from solders.transaction import VersionedTransaction as SoldersVersionedTransaction

from solathon.core.compute_budget import set_compute_unit_limit
from solathon.core.instructions import AccountMeta, Instruction, transfer
from solathon.core.layouts import SYSTEM_PROGRAM_ID
from solathon.keypair import Keypair
from solathon.publickey import PublicKey
from solathon.transaction import Transaction
from solathon.versioned import (
    AddressLookupTableAccount,
    MessageAddressTableLookup,
    MessageV0,
    MessageV1,
    TransactionConfig,
    VersionedTransaction,
)


def _native_instruction(instruction: Instruction) -> SoldersInstruction:
    return SoldersInstruction(
        instruction.program_id.to_solders(),
        instruction.data,
        [
            SoldersAccountMeta(
                meta.public_key.to_solders(), meta.is_signer, meta.is_writable
            )
            for meta in instruction.keys
        ],
    )


def _v1_config() -> TransactionConfig:
    return TransactionConfig(
        priority_fee=1_000,
        compute_unit_limit=200_000,
        loaded_accounts_data_size_limit=64_000,
    )


def test_keypair_solders_conversion_preserves_canonical_bytes_and_signatures() -> None:
    seed = bytes(range(32))
    keypair = Keypair(seed)

    assert Keypair.from_seed(seed).public_key == keypair.public_key
    assert Keypair.from_private_key(bytes(keypair)).public_key == keypair.public_key
    assert len(bytes(keypair)) == 64
    assert bytes(Keypair.from_solders(keypair.to_solders())) == bytes(keypair)
    assert keypair.to_solders().pubkey() == keypair.public_key.to_solders()
    assert len(keypair.sign(b"message").signature) == 64
    with pytest.raises(TypeError, match="bytes-like"):
        Keypair.from_seed(32)  # type: ignore[arg-type]


def test_address_lookup_table_decodes_real_account_state() -> None:
    table_key = PublicKey(bytes([9]) * 32)
    addresses = [PublicKey(bytes([10]) * 32), PublicKey(bytes([11]) * 32)]
    serialized_meta = b"\x01\x00\x00\x00" + bytes(LookupTableMeta())
    account_data = serialized_meta.ljust(56, b"\x00") + b"".join(
        bytes(address) for address in addresses
    )

    table = AddressLookupTableAccount.from_account_data(table_key, account_data)

    assert table.key == table_key
    assert tuple(table.addresses) == tuple(addresses)
    assert table == AddressLookupTableAccount.deserialize(table_key, account_data)
    assert AddressLookupTableAccount.from_solders(table.to_solders()) == table

    with pytest.raises(ValueError, match="56-byte metadata"):
        AddressLookupTableAccount.from_account_data(table_key, bytes(55))
    with pytest.raises(ValueError, match="partial 32-byte address"):
        AddressLookupTableAccount.from_account_data(table_key, account_data + b"x")
    with pytest.raises(ValueError, match="Invalid address lookup table"):
        AddressLookupTableAccount.from_account_data(table_key, bytes(56))
    with pytest.raises(TypeError, match="bytes-like"):
        AddressLookupTableAccount.from_account_data(
            table_key,
            56,  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="sequence of public keys"):
        AddressLookupTableAccount(table_key, bytes(32))  # type: ignore[arg-type]


def test_lookup_indexes_and_versioned_buffers_require_bytes_like_values() -> None:
    with pytest.raises(TypeError, match="indexes must be bytes-like"):
        MessageAddressTableLookup(
            PublicKey(bytes([9]) * 32),
            1,  # type: ignore[arg-type]
            b"",
        )
    with pytest.raises(TypeError, match="message buffer must be bytes-like"):
        MessageV0.from_buffer(1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="transaction buffer must be bytes-like"):
        VersionedTransaction.from_buffer(1)  # type: ignore[arg-type]


def test_v0_alt_compile_and_transaction_match_solders_exactly() -> None:
    payer = Keypair(bytes(range(32)))
    recipient = PublicKey(bytes([7]) * 32)
    table_key = PublicKey(bytes([8]) * 32)
    instruction = transfer(payer.public_key, recipient, 12_345)
    blockhash = Hash.default()
    table = AddressLookupTableAccount(table_key, [recipient])

    message = MessageV0.compile(
        payer.public_key, [instruction], blockhash, lookup_tables=[table]
    )
    native_message = SoldersMessageV0.try_compile(
        payer.public_key.to_solders(),
        [_native_instruction(instruction)],
        [
            SoldersAddressLookupTableAccount(
                table_key.to_solders(), [recipient.to_solders()]
            )
        ],
        blockhash,
    )

    assert message.serialize() == to_bytes_versioned(native_message)
    assert message.to_solders() == native_message
    assert message.address_table_lookups[0].writable_indexes == b"\x00"
    recipient_index = message.instructions[0].accounts[1]
    assert recipient_index >= len(message.static_account_keys)
    assert message.is_account_signer(recipient_index) == native_message.is_signer(
        recipient_index
    )
    assert message.is_account_writable(
        recipient_index
    ) == native_message.is_maybe_writable(recipient_index)

    transaction = VersionedTransaction(message, [payer])
    transaction.sign()
    wire = transaction.serialize()
    native_transaction = SoldersVersionedTransaction(
        native_message, [payer.to_solders()]
    )

    assert wire == bytes(native_transaction)
    parsed = VersionedTransaction.from_buffer(wire)
    assert parsed.version == 0
    assert parsed.message.serialize() == message.serialize()
    assert parsed.verify_signatures()
    assert parsed.serialize() == wire


def test_v0_supports_partial_signing_then_external_signature() -> None:
    payer = Keypair(bytes(range(32)))
    cosigner = Keypair(bytes(range(1, 33)))
    instruction = Instruction(
        keys=[AccountMeta(cosigner.public_key, True, False)],
        program_id=SYSTEM_PROGRAM_ID,
        data=b"\x00",
    )
    message = MessageV0.compile(payer.public_key, [instruction], Hash.default())
    transaction = VersionedTransaction(message, [payer])

    transaction.sign()
    partial_wire = transaction.serialize(require_all_signatures=False)
    assert len(partial_wire) > len(message.serialize())
    assert not transaction.verify_signatures()
    assert transaction.verify_present_signatures()

    cosigner_signature = cosigner.to_solders().sign_message(message.serialize())
    transaction.add_signature(cosigner.public_key, cosigner_signature)

    assert transaction.verify_signatures()
    assert VersionedTransaction.from_buffer(transaction.serialize()).verify_signatures()


def test_v0_signature_verification_is_false_for_malformed_public_state() -> None:
    payer = Keypair(bytes(range(32)))
    message = MessageV0.compile(payer.public_key, [], Hash.default())
    transaction = VersionedTransaction(message)
    transaction.signatures[0] = b"short"

    assert not transaction.verify_signatures()
    assert not transaction.verify_present_signatures()

    with pytest.raises(TypeError, match="legacy Message"):
        Transaction.populate(message, [bytes(64)])


def test_v0_enforces_the_udp_packet_limit() -> None:
    payer = Keypair(bytes(range(32)))
    instruction = Instruction([], SYSTEM_PROGRAM_ID, bytes(1_200))
    message = MessageV0.compile(payer.public_key, [instruction], Hash.default())
    transaction = VersionedTransaction(message, [payer])
    transaction.sign()

    with pytest.raises(ValueError, match="1232-byte limit"):
        transaction.serialize()


def test_versioned_parsers_reject_structurally_invalid_native_wires() -> None:
    payer = Keypair(bytes(range(32)))
    bad_v0 = SoldersMessageV0(
        SoldersMessageHeader(1, 0, 0),
        [payer.public_key.to_solders()],
        Hash.default(),
        [SoldersCompiledInstruction(1, b"", b"")],
        [],
    )
    bad_v0_wire = to_bytes_versioned(bad_v0)
    with pytest.raises(ValueError, match="Invalid MessageV0"):
        MessageV0.from_buffer(bad_v0_wire)

    bad_v1 = SoldersMessageV1(
        SoldersMessageHeader(1, 0, 0),
        _v1_config().to_solders(),
        Hash.default(),
        [payer.public_key.to_solders()],
        [SoldersCompiledInstruction(1, b"", b"")],
    )
    bad_v1_wire = to_bytes_versioned(bad_v1)
    with pytest.raises(ValueError, match="Invalid MessageV1"):
        MessageV1.from_buffer(bad_v1_wire)

    bad_transaction = SoldersVersionedTransaction.populate(
        bad_v0, [SoldersSignature.default()]
    )
    with pytest.raises(ValueError, match="Invalid versioned transaction"):
        VersionedTransaction.from_buffer(bytes(bad_transaction))


def test_v1_compile_sign_and_parse_match_solders_exactly() -> None:
    payer = Keypair(bytes(range(32)))
    recipient = PublicKey(bytes([7]) * 32)
    instruction = transfer(payer.public_key, recipient, 42)
    blockhash = Hash.default()
    config = _v1_config()

    message = MessageV1.compile(payer.public_key, [instruction], blockhash, config)
    native_config = SoldersTransactionConfig(
        priority_fee=1_000,
        compute_unit_limit=200_000,
        loaded_accounts_data_size_limit=64_000,
    )
    native_message = SoldersMessageV1.try_compile(
        payer.public_key.to_solders(),
        [_native_instruction(instruction)],
        blockhash,
        native_config,
    )

    assert message.serialize() == to_bytes_versioned(native_message)
    assert message.to_solders() == native_message

    transaction = VersionedTransaction(message, [payer])
    transaction.sign()
    wire = transaction.serialize()
    native_transaction = SoldersVersionedTransaction(
        native_message, [payer.to_solders()]
    )

    assert wire == bytes(native_transaction)
    assert wire[0] == 0x81
    assert wire[-64:] == bytes(native_transaction.signatures[0])

    parsed = VersionedTransaction.from_buffer(wire)
    assert parsed.version == 1
    assert parsed.message.config == config
    assert parsed.verify_signatures()
    assert parsed.serialize() == wire


@pytest.mark.parametrize(
    "config, field",
    [
        (
            TransactionConfig(loaded_accounts_data_size_limit=64_000),
            "compute_unit_limit",
        ),
        (
            TransactionConfig(
                compute_unit_limit=200_000,
                loaded_accounts_data_size_limit=0,
            ),
            "loaded_accounts_data_size_limit",
        ),
    ],
)
def test_v1_requires_explicit_positive_execution_limits(
    config: TransactionConfig, field: str
) -> None:
    payer = Keypair(bytes(range(32)))

    with pytest.raises(ValueError, match=field):
        MessageV1.compile(payer.public_key, [], Hash.default(), config)


def test_v1_rejects_lookup_tables_and_compute_budget_instructions() -> None:
    payer = Keypair(bytes(range(32)))
    table = AddressLookupTableAccount(PublicKey(bytes([9]) * 32), [])

    with pytest.raises(ValueError, match="does not support address lookup tables"):
        MessageV1.compile(
            payer.public_key,
            [],
            Hash.default(),
            _v1_config(),
            lookup_tables=[table],
        )

    with pytest.raises(ValueError, match="no-ops in MessageV1"):
        MessageV1.compile(
            payer.public_key,
            [set_compute_unit_limit(200_000)],
            Hash.default(),
            _v1_config(),
        )


def test_v1_enforces_its_4096_byte_transaction_limit() -> None:
    payer = Keypair(bytes(range(32)))
    instruction = Instruction([], SYSTEM_PROGRAM_ID, bytes(4_000))
    message = MessageV1.compile(
        payer.public_key, [instruction], Hash.default(), _v1_config()
    )
    transaction = VersionedTransaction(message, [payer])
    transaction.sign()

    with pytest.raises(ValueError, match="4096-byte limit"):
        transaction.serialize()
