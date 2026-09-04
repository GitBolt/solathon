from __future__ import annotations

from decimal import Decimal

import pytest
from solders.pubkey import Pubkey
from solders.token.associated import get_associated_token_address as solders_ata

from solathon.core.layouts import SYSVAR_RENT_ID
from solathon.publickey import PublicKey
from solathon.token import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    MINT_BASE_SIZE,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_ACCOUNT_BASE_SIZE,
    TOKEN_PROGRAM_ID,
    TLVExtension,
    TokenAccountState,
    TokenExtensionType,
    UnsupportedTokenExtensionError,
    create_associated_token_account,
    get_associated_token_address,
    parse_mint,
    parse_tlv_extensions,
    parse_token_account,
    token_amount_to_base_units,
    transfer_checked,
)


def key(start: int) -> PublicKey:
    return PublicKey(bytes((start + index) % 256 for index in range(32)))


def option_key(value: PublicKey | None) -> bytes:
    if value is None:
        return bytes(36)
    return (1).to_bytes(4, "little") + bytes(value)


def mint_base(
    authority: PublicKey,
    *,
    supply: int = 123_456,
    decimals: int = 6,
    initialized: bool = True,
) -> bytes:
    return b"".join(
        [
            option_key(authority),
            supply.to_bytes(8, "little"),
            bytes([decimals, initialized]),
            option_key(None),
        ]
    )


def token_account_base(mint: PublicKey, owner: PublicKey) -> bytes:
    return b"".join(
        [
            bytes(mint),
            bytes(owner),
            (999).to_bytes(8, "little"),
            option_key(None),
            bytes([TokenAccountState.INITIALIZED]),
            (1).to_bytes(4, "little") + (2_039_280).to_bytes(8, "little"),
            (5).to_bytes(8, "little"),
            option_key(None),
        ]
    )


def test_program_aware_associated_token_address_matches_solders() -> None:
    owner = key(1)
    mint = key(80)

    classic = get_associated_token_address(owner, mint)
    assert classic.to_solders() == solders_ata(owner.to_solders(), mint.to_solders())

    token_2022 = get_associated_token_address(owner, mint, TOKEN_2022_PROGRAM_ID)
    expected, _ = Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_2022_PROGRAM_ID), bytes(mint)],
        ASSOCIATED_TOKEN_PROGRAM_ID.to_solders(),
    )
    assert token_2022.to_solders() == expected
    assert token_2022 != classic


def test_associated_token_create_is_idempotent_and_program_aware() -> None:
    payer, owner, mint = key(2), key(3), key(4)
    instruction = create_associated_token_account(
        payer,
        owner,
        mint,
        token_program_id=TOKEN_2022_PROGRAM_ID,
    )

    assert instruction.program_id == ASSOCIATED_TOKEN_PROGRAM_ID
    assert instruction.data == b"\x01"
    assert instruction.keys[0].public_key == payer
    assert instruction.keys[0].is_signer and instruction.keys[0].is_writable
    assert instruction.keys[1].public_key == get_associated_token_address(
        owner, mint, TOKEN_2022_PROGRAM_ID
    )
    assert instruction.keys[-1].public_key == TOKEN_2022_PROGRAM_ID

    legacy_create = create_associated_token_account(
        payer,
        owner,
        mint,
        token_program_id=TOKEN_2022_PROGRAM_ID,
        idempotent=False,
    )
    assert legacy_create.data == b""
    assert legacy_create.keys[-2].public_key == TOKEN_2022_PROGRAM_ID
    assert legacy_create.keys[-1].public_key == SYSVAR_RENT_ID


def test_transfer_checked_wire_and_multisig_accounts() -> None:
    source, mint, destination, authority = key(5), key(6), key(7), key(8)
    instruction = transfer_checked(
        source,
        mint,
        destination,
        authority,
        500_000,
        6,
        token_program_id=TOKEN_2022_PROGRAM_ID,
    )

    assert instruction.program_id == TOKEN_2022_PROGRAM_ID
    assert instruction.data == b"\x0c" + (500_000).to_bytes(8, "little") + b"\x06"
    assert [meta.is_signer for meta in instruction.keys] == [False, False, False, True]
    assert [meta.is_writable for meta in instruction.keys] == [True, False, True, False]

    signers = [key(9), key(10)]
    multisig = transfer_checked(
        source,
        mint,
        destination,
        authority,
        1,
        0,
        multisig_signers=signers,
    )
    assert not multisig.keys[3].is_signer
    assert [meta.public_key for meta in multisig.keys[4:]] == signers
    assert all(meta.is_signer and not meta.is_writable for meta in multisig.keys[4:])


def test_checked_transfer_rejects_extensions_needing_specialized_logic() -> None:
    args = (key(11), key(12), key(13), key(14), 1, 0)
    with pytest.raises(UnsupportedTokenExtensionError, match="transfer-fee"):
        transfer_checked(
            *args,
            token_program_id=TOKEN_2022_PROGRAM_ID,
            extensions=[TLVExtension(TokenExtensionType.TRANSFER_FEE_CONFIG, b"")],
        )
    with pytest.raises(UnsupportedTokenExtensionError, match="extra account metas"):
        transfer_checked(
            *args,
            token_program_id=TOKEN_2022_PROGRAM_ID,
            extensions=[TokenExtensionType.TRANSFER_HOOK],
        )
    with pytest.raises(UnsupportedTokenExtensionError, match="non-transferable"):
        transfer_checked(
            *args,
            token_program_id=TOKEN_2022_PROGRAM_ID,
            extensions=[TokenExtensionType.NON_TRANSFERABLE_ACCOUNT],
        )
    with pytest.raises(UnsupportedTokenExtensionError, match="unknown Token-2022"):
        transfer_checked(
            *args,
            token_program_id=TOKEN_2022_PROGRAM_ID,
            extensions=[TLVExtension(65_535, b"")],
        )


def test_token_amount_conversion_is_exact() -> None:
    assert token_amount_to_base_units(Decimal("1.25"), 6) == 1_250_000
    assert token_amount_to_base_units("0", 9) == 0
    with pytest.raises(ValueError, match="more than 2 decimal places"):
        token_amount_to_base_units("0.001", 2)
    with pytest.raises(ValueError, match="64-bit"):
        token_amount_to_base_units(2**64, 0)


def test_parse_legacy_mint_and_token_account_base_layouts() -> None:
    authority, mint, owner = key(20), key(21), key(22)
    mint_data = mint_base(authority)
    assert len(mint_data) == MINT_BASE_SIZE
    parsed_mint = parse_mint(mint_data)
    assert parsed_mint.mint_authority == authority
    assert parsed_mint.supply == 123_456
    assert parsed_mint.decimals == 6
    assert parsed_mint.is_initialized
    assert parsed_mint.freeze_authority is None
    assert parsed_mint.program_id == TOKEN_PROGRAM_ID
    assert parsed_mint.extensions == ()

    account_data = token_account_base(mint, owner)
    assert len(account_data) == TOKEN_ACCOUNT_BASE_SIZE
    account = parse_token_account(account_data)
    assert account.mint == mint
    assert account.owner == owner
    assert account.amount == 999
    assert account.is_initialized and account.is_native and not account.is_frozen
    assert account.rent_exempt_reserve == 2_039_280
    assert account.delegated_amount == 5


def test_parse_token_2022_padding_and_preserve_unknown_tlv() -> None:
    authority = key(30)
    unknown_type = 60_000
    tlv = unknown_type.to_bytes(2, "little") + (3).to_bytes(2, "little") + b"xyz"
    data = mint_base(authority) + bytes(83) + b"\x01" + tlv

    mint = parse_mint(data, TOKEN_2022_PROGRAM_ID)
    assert mint.program_id == TOKEN_2022_PROGRAM_ID
    assert mint.extensions == (TLVExtension(unknown_type, b"xyz"),)
    assert mint.extensions[0].extension_type is None


def test_parse_token_2022_account_extensions() -> None:
    mint, owner = key(31), key(32)
    extension = int(TokenExtensionType.IMMUTABLE_OWNER).to_bytes(2, "little") + (
        0
    ).to_bytes(2, "little")
    data = token_account_base(mint, owner) + b"\x02" + extension
    account = parse_token_account(data, TOKEN_2022_PROGRAM_ID)
    assert account.has_extension(TokenExtensionType.IMMUTABLE_OWNER)


def test_tlv_and_state_parsers_reject_truncation_or_wrong_program() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        parse_tlv_extensions(b"\x03\x00\x05\x00x")
    with pytest.raises(ValueError, match="cannot contain"):
        parse_mint(mint_base(key(40)) + b"extra")
    with pytest.raises(ValueError, match="account type"):
        parse_mint(mint_base(key(41)) + bytes(83) + b"\x02", TOKEN_2022_PROGRAM_ID)
