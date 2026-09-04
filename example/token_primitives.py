"""Build Token and Token-2022 primitives without submitting a transaction."""

from __future__ import annotations

from decimal import Decimal

from solathon import PublicKey
from solathon.core.instructions import Instruction
from solathon.token import (
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    TokenAccount,
    TokenMint,
    create_associated_token_account,
    get_associated_token_address,
    parse_mint,
    parse_token_account,
    token_amount_to_base_units,
    transfer_checked,
)


def checked_transfer_from_state(
    *,
    mint_key: PublicKey,
    source_key: PublicKey,
    destination_key: PublicKey,
    authority: PublicKey,
    mint_data: bytes,
    source_data: bytes,
    destination_data: bytes,
) -> tuple[TokenMint, TokenAccount, TokenAccount, Instruction]:
    """Parse Token-2022 state and refuse unsafe generic extension transfers."""

    mint = parse_mint(mint_data, TOKEN_2022_PROGRAM_ID)
    source = parse_token_account(source_data, TOKEN_2022_PROGRAM_ID)
    destination = parse_token_account(destination_data, TOKEN_2022_PROGRAM_ID)
    if source.mint != mint_key or destination.mint != mint_key:
        raise ValueError("source and destination must belong to the requested mint")
    if source.owner != authority:
        raise ValueError("authority does not own the source token account")
    instruction = transfer_checked(
        source_key,
        mint_key,
        destination_key,
        authority,
        token_amount_to_base_units(Decimal("1.25"), mint.decimals),
        mint.decimals,
        token_program_id=TOKEN_2022_PROGRAM_ID,
        extensions=[mint, source, destination],
    )
    return mint, source, destination, instruction


def main() -> None:
    payer = PublicKey(bytes(range(32)))
    owner = PublicKey(bytes(range(32, 64)))
    mint = PublicKey(bytes(range(64, 96)))

    classic_ata = get_associated_token_address(owner, mint, TOKEN_PROGRAM_ID)
    token_2022_ata = get_associated_token_address(
        owner,
        mint,
        TOKEN_2022_PROGRAM_ID,
    )
    assert classic_ata != token_2022_ata

    create_ata = create_associated_token_account(
        payer,
        owner,
        mint,
        token_program_id=TOKEN_2022_PROGRAM_ID,
        idempotent=True,
    )
    print("classic ATA:", classic_ata)
    print("Token-2022 ATA:", token_2022_ata)
    print("idempotent create instruction:", create_ata)
    print("1.25 tokens at six decimals:", token_amount_to_base_units("1.25", 6))


if __name__ == "__main__":
    main()
