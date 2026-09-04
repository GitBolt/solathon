from decimal import Decimal

import pytest
from nacl.exceptions import BadSignatureError
from solders.pubkey import Pubkey
from solders.system_program import (
    create_account_allow_prefund as solders_create_account_allow_prefund,
)
from solders.system_program import (
    upgrade_nonce_account as solders_upgrade_nonce_account,
)

from solathon import PublicKey
from solathon.core.instructions import (
    create_account_allow_prefund,
    upgrade_nonce_account,
)
from solathon.utils import (
    MAX_LAMPORTS,
    lamport_to_sol,
    lamport_to_sol_decimal,
    sol_to_lamport,
    verify_signature,
)


def test_public_key_is_immutable_and_matches_solders() -> None:
    raw = bytes(range(32))
    key = PublicKey(raw)

    assert bytes(key) == raw
    assert str(key) == str(Pubkey.from_bytes(raw))
    assert PublicKey(str(key)) == key
    assert PublicKey(int.from_bytes(raw, "big")) == key
    assert key.to_solders() == Pubkey.from_bytes(raw)
    with pytest.raises(AttributeError):
        key.byte_value = bytes(32)  # type: ignore[misc]
    with pytest.raises(TypeError, match="boolean"):
        PublicKey(True)


def test_program_address_matches_solders() -> None:
    program = PublicKey(bytes(range(32, 64)))
    seeds = [b"vault", bytes(range(32))]

    address, bump = PublicKey.find_program_address(seeds, program)
    solders_address, solders_bump = Pubkey.find_program_address(
        seeds, program.to_solders()
    )

    assert address.to_solders() == solders_address
    assert bump == solders_bump
    assert (
        PublicKey.create_program_address([*seeds, bytes([bump])], program).to_solders()
        == solders_address
    )


def test_program_address_rejects_oversized_seeds() -> None:
    program = PublicKey(bytes(32))
    with pytest.raises(ValueError, match="32 bytes"):
        PublicKey.find_program_address([bytes(33)], program)
    with pytest.raises(ValueError, match="at most 15 seeds"):
        PublicKey.find_program_address([b""] * 16, program)
    with pytest.raises(ValueError, match="valid address"):
        PublicKey.create_program_address([b"x"] * 16, program)
    with pytest.raises(ValueError, match="16 seeds"):
        PublicKey.create_program_address([b""] * 17, program)


def test_exact_lamport_conversions() -> None:
    assert sol_to_lamport(Decimal("1.000000001")) == 1_000_000_001
    assert sol_to_lamport("0.000000001") == 1
    assert lamport_to_sol_decimal(1_000_000_001) == Decimal("1.000000001")
    assert lamport_to_sol(1_000_000_001) == 1.000000001

    with pytest.raises(ValueError, match="fractional lamports"):
        sol_to_lamport("0.0000000001")
    with pytest.raises(ValueError, match="unsigned"):
        sol_to_lamport(-1)
    with pytest.raises(ValueError, match="unsigned"):
        lamport_to_sol_decimal(MAX_LAMPORTS + 1)


def test_verify_signature_accepts_text_public_key() -> None:
    from nacl.signing import SigningKey

    signing_key = SigningKey(bytes(range(32)))
    public_key = PublicKey(bytes(signing_key.verify_key))
    message = b"solathon"
    signature = signing_key.sign(message).signature

    verify_signature(str(public_key), signature, message)
    with pytest.raises(BadSignatureError):
        verify_signature(str(public_key), signature, b"different")


def test_new_system_instructions_match_solders() -> None:
    new_account = PublicKey(bytes([1]) * 32)
    payer = PublicKey(bytes([2]) * 32)
    owner = PublicKey(bytes([3]) * 32)

    ours = upgrade_nonce_account(new_account)
    reference = solders_upgrade_nonce_account(
        {"nonce_pubkey": new_account.to_solders()}
    )
    assert ours.data == bytes(reference.data)
    assert [(key.is_signer, key.is_writable) for key in ours.keys] == [
        (key.is_signer, key.is_writable) for key in reference.accounts
    ]

    ours = create_account_allow_prefund(new_account, 5, 8, owner, payer)
    reference = solders_create_account_allow_prefund(
        {
            "new_account": new_account.to_solders(),
            "payer": payer.to_solders(),
            "lamports": 5,
            "space": 8,
            "owner": owner.to_solders(),
        }
    )
    assert ours.data == bytes(reference.data)
    assert [key.public_key.to_solders() for key in ours.keys] == [
        key.pubkey for key in reference.accounts
    ]
