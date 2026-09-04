import base64

import pytest
from base58 import b58decode
from solders.hash import Hash
from solders.instruction import CompiledInstruction as SoldersCompiledInstruction
from solders.message import Message as SoldersMessage
from solders.system_program import (
    advance_nonce_account as solders_advance_nonce_account,
)
from solders.system_program import transfer as solders_transfer
from solders.transaction import Transaction as SoldersTransaction

from solathon import NonceInformation, PrivateKey
from solathon.core.instructions import (
    AccountMeta,
    Instruction,
    advance_nonce_account,
    transfer,
)
from solathon.core.layouts import SYSTEM_PROGRAM_ID
from solathon.keypair import Keypair
from solathon.publickey import PublicKey
from solathon.transaction import DEFAULT_SIGNATURE, Transaction

GOLDEN_LEGACY_TRANSACTION = "AUHlvMM1AURr4qS5CNbBph98Ra7JROvtdEcEUlxdJ/wP0CMeIINvkilGgCwWkZN8eePexkNtfU4tT7pzf4MPiA0BAAEDA6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbggISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+PwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcBAgIAAQwCAAAAFc1bBwAAAAA="


def _blockhash() -> str:
    return str(Hash.from_bytes(bytes([7]) * 32))


def test_legacy_transaction_matches_fixed_wire_vector() -> None:
    payer = Keypair(bytes(range(32)))
    recipient = PublicKey(bytes(range(32, 64)))
    transaction = Transaction(
        fee_payer=payer.public_key,
        signers=[payer],
        recent_blockhash=_blockhash(),
        instructions=[transfer(payer.public_key, recipient, 123_456_789)],
    )

    transaction.sign()
    wire = transaction.serialize()

    assert base64.b64encode(wire).decode() == GOLDEN_LEGACY_TRANSACTION
    assert bytes(SoldersTransaction.from_bytes(wire)) == wire


def test_legacy_round_trip_preserves_signatures_and_message() -> None:
    wire = base64.b64decode(GOLDEN_LEGACY_TRANSACTION)
    transaction = Transaction.from_buffer(wire)

    assert transaction.verify_signatures()
    assert transaction.serialize() == wire
    assert transaction.fee_payer == Keypair(bytes(range(32))).public_key


def test_durable_nonce_instruction_is_first_and_matches_solders() -> None:
    payer = Keypair(bytes(range(32)))
    nonce_account = PublicKey(bytes([8]) * 32)
    recipient = PublicKey(bytes(range(32, 64)))
    durable_nonce = str(Hash.from_bytes(bytes([9]) * 32))
    nonce_instruction = advance_nonce_account(nonce_account, payer.public_key)
    payment = transfer(payer.public_key, recipient, 123)
    transaction = Transaction(
        fee_payer=payer.public_key,
        nonce_info=NonceInformation(durable_nonce, nonce_instruction),
        signers=[payer],
        instructions=[payment],
    )

    native_nonce_instruction = solders_advance_nonce_account(
        {
            "nonce_pubkey": nonce_account.to_solders(),
            "authorized_pubkey": payer.public_key.to_solders(),
        }
    )
    native_payment = solders_transfer(
        {
            "from_pubkey": payer.public_key.to_solders(),
            "to_pubkey": recipient.to_solders(),
            "lamports": 123,
        }
    )

    message = transaction._message_and_signatures()
    first, second = message.instructions
    assert message.recent_blockhash == durable_nonce
    assert b58decode(first.data) == bytes(native_nonce_instruction.data)
    assert [message.account_keys[index].to_solders() for index in first.accounts] == [
        meta.pubkey for meta in native_nonce_instruction.accounts
    ]
    assert b58decode(second.data) == bytes(native_payment.data)
    assert [message.account_keys[index].to_solders() for index in second.accounts] == [
        meta.pubkey for meta in native_payment.accounts
    ]
    assert transaction.instructions == [payment]
    transaction.sign()
    assert transaction.verify_signatures()


def test_nonce_information_rejects_noncanonical_advance_instruction() -> None:
    authority = Keypair(bytes(range(32)))
    nonce_account = PublicKey(bytes([8]) * 32)
    durable_nonce = str(Hash.from_bytes(bytes([9]) * 32))

    with pytest.raises(ValueError, match="AdvanceNonceAccount instruction"):
        NonceInformation(
            durable_nonce,
            transfer(authority.public_key, nonce_account, 1),
        )

    wrong_accounts = advance_nonce_account(nonce_account, authority.public_key)
    wrong_accounts.keys[0].is_writable = False
    with pytest.raises(ValueError, match="canonical AdvanceNonceAccount accounts"):
        NonceInformation(durable_nonce, wrong_accounts)


def test_legacy_round_trip_preserves_unused_static_accounts() -> None:
    payer = Keypair(bytes(range(32)))
    recipient = PublicKey(bytes(range(32, 64)))
    unused = PublicKey(bytes([9]) * 32)
    payment = transfer(payer.public_key, recipient, 1)
    message = SoldersMessage.new_with_compiled_instructions(
        1,
        0,
        2,
        [
            payer.public_key.to_solders(),
            recipient.to_solders(),
            SYSTEM_PROGRAM_ID.to_solders(),
            unused.to_solders(),
        ],
        Hash.default(),
        [SoldersCompiledInstruction(2, payment.data, bytes([0, 1]))],
    )
    wire = bytes(SoldersTransaction([payer.to_solders()], message, Hash.default()))

    transaction = Transaction.from_buffer(wire)

    assert len(transaction._message_and_signatures().account_keys) == 4
    assert transaction.verify_signatures()
    assert transaction.serialize() == wire


def test_legacy_round_trip_preserves_valid_empty_instruction_message() -> None:
    payer = Keypair(bytes(range(32)))
    message = SoldersMessage.new_with_blockhash(
        [], payer.public_key.to_solders(), Hash.default()
    )
    wire = bytes(SoldersTransaction([payer.to_solders()], message, Hash.default()))

    transaction = Transaction.from_buffer(wire)

    assert transaction.instructions == []
    assert transaction.verify_signatures()
    assert transaction.serialize() == wire


def test_private_key_string_and_repr_do_not_expose_secret_material() -> None:
    private_key = Keypair(bytes(range(32))).private_key

    assert isinstance(private_key, PrivateKey)
    assert str(private_key) == "<redacted>"
    assert "<redacted>" in repr(private_key)
    assert private_key.base58_encode() != b"<redacted>"
    with pytest.raises(TypeError, match="bytes-like"):
        PrivateKey(64)  # type: ignore[arg-type]


def test_signature_verification_is_false_for_malformed_public_state() -> None:
    transaction = Transaction.from_buffer(base64.b64decode(GOLDEN_LEGACY_TRANSACTION))
    assert not transaction.verify_signatures(b"")
    assert not transaction.verify_present_signatures(b"")

    transaction.signatures[0].signature = b"short"

    assert not transaction.verify_signatures()
    assert not transaction.verify_present_signatures()


def test_fee_payer_is_first_even_when_signers_are_supplied_out_of_order() -> None:
    payer = Keypair(bytes(range(32)))
    other = Keypair(bytes(range(1, 33)))
    instruction = Instruction(
        keys=[AccountMeta(other.public_key, True, False)],
        program_id=PublicKey(bytes([9]) * 32),
        data=b"test",
    )
    transaction = Transaction(
        fee_payer=payer.public_key,
        signers=[other, payer],
        recent_blockhash=_blockhash(),
        instructions=[instruction],
    )

    message = transaction._message_and_signatures()

    assert message.account_keys[:2] == [payer.public_key, other.public_key]
    assert [pair.public_key for pair in transaction.signatures] == [
        payer.public_key,
        other.public_key,
    ]


def test_instruction_signer_is_required_even_when_keypair_is_absent() -> None:
    payer = Keypair(bytes(range(32)))
    absent_signer = PublicKey(bytes(range(32, 64)))
    instruction = Instruction(
        keys=[AccountMeta(absent_signer, True, False)],
        program_id=PublicKey(bytes([9]) * 32),
        data=b"test",
    )
    transaction = Transaction(
        fee_payer=payer.public_key,
        signers=[payer],
        recent_blockhash=_blockhash(),
        instructions=[instruction],
    )

    transaction.sign()

    assert len(transaction.signatures) == 2
    assert transaction.signatures[0].signature is not None
    assert transaction.signatures[1].signature is None
    with pytest.raises(ValueError, match="missing"):
        transaction.serialize()
    partial = transaction.serialize(require_all_signatures=False)
    parsed = SoldersTransaction.from_bytes(partial)
    assert bytes(parsed.signatures[1]) == DEFAULT_SIGNATURE


def test_transaction_rejects_empty_and_malformed_inputs() -> None:
    with pytest.raises(ValueError, match="no instructions"):
        Transaction(recent_blockhash=_blockhash()).compile_transaction()
    with pytest.raises(ValueError):
        Transaction.from_buffer(b"")
    with pytest.raises(ValueError):
        Transaction.from_buffer(base64.b64decode(GOLDEN_LEGACY_TRANSACTION)[:-1])
    with pytest.raises(ValueError, match="1232-byte packet limit"):
        Transaction.from_buffer(bytes(1_233))
