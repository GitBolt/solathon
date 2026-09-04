from __future__ import annotations

import base64
import binascii
from collections.abc import Sequence
from typing import Any, cast

from ..client import Client
from ..core.instructions import (
    MEMO_PROGRAM_ID,
    AccountMeta,
    Instruction,
    transfer,
)
from ..core.layouts import SYSTEM_PROGRAM_ID
from ..core.types import Commitment
from ..core.types.account_info import AccountInfo, AccountInfoType
from ..core.types.block import BlockHash
from ..keypair import Keypair
from ..publickey import PublicKey
from ..token import (
    TOKEN_PROGRAM_IDS,
    TokenAccount,
    TokenAccountState,
    TokenExtensionType,
    TokenMint,
    UnsupportedTokenExtensionError,
    get_associated_token_address,
    parse_mint,
    parse_token_account,
    token_amount_to_base_units,
    transfer_checked,
)
from ..transaction import Transaction
from ..utils import sol_to_lamport, unwrap_rpc_response
from .types import CreateTransferFields

MAX_TOKEN_ACCOUNT_DATA_BYTES = 1024 * 1024

_UNSUPPORTED_PAY_AMOUNT_EXTENSIONS = {
    TokenExtensionType.INTEREST_BEARING_CONFIG: (
        "interest-bearing mints require timestamp-aware UI amount conversion"
    ),
    TokenExtensionType.SCALED_UI_AMOUNT: (
        "scaled-UI-amount mints require multiplier-aware UI amount conversion"
    ),
}


def create_transfer(
    client: Client,
    sender: Keypair,
    transfer_fields: CreateTransferFields,
    commitment: Commitment | None = None,
) -> Transaction:
    """Create a native-SOL, SPL Token, or Token-2022 Solana Pay transaction.

    The memo (when present) is placed immediately before the payment transfer,
    and the transfer is always last as required by the Solana Pay spec.

    Basic Token-2022 transfers are supported. Extensions that need specialized
    amount conversion, instructions, or accounts are rejected explicitly.
    """

    if not isinstance(sender, Keypair):
        raise TypeError("sender must be a Keypair")
    recipient = transfer_fields.get("recipient")
    amount = transfer_fields.get("amount")
    if not isinstance(recipient, PublicKey):
        raise ValueError("recipient must be a PublicKey")
    if amount is None:
        raise ValueError("amount is missing from transfer_fields")

    memo = transfer_fields.get("memo")
    if memo is not None and not isinstance(memo, str):
        raise TypeError("memo must be a string")

    mint = transfer_fields.get("spl_token")
    if mint is None:
        instruction = _create_native_instruction(
            client, sender, recipient, amount, commitment
        )
    else:
        if not isinstance(mint, PublicKey):
            raise ValueError("spl_token must be a PublicKey")
        instruction = _create_token_instruction(
            client, sender, recipient, mint, amount, memo, commitment
        )

    for reference in _references(transfer_fields.get("reference")):
        instruction.keys.append(AccountMeta(reference, False, False))

    blockhash = client.get_latest_blockhash(commitment=commitment)
    if isinstance(blockhash, dict):
        value = unwrap_rpc_response(blockhash)
        if not isinstance(value, dict) or not isinstance(value.get("value"), dict):
            raise ValueError("Latest-blockhash RPC response is malformed")
        blockhash = BlockHash(value["value"])
    if not isinstance(blockhash, BlockHash):
        raise ValueError("Latest-blockhash RPC response is malformed")

    instructions = []
    if memo is not None:
        instructions.append(
            Instruction(
                keys=[AccountMeta(sender.public_key, True, False)],
                program_id=MEMO_PROGRAM_ID,
                data=memo.encode("utf-8"),
            )
        )
    instructions.append(instruction)

    return Transaction(
        instructions=instructions,
        signers=[sender],
        fee_payer=sender.public_key,
        recent_blockhash=blockhash.blockhash,
    )


def _create_native_instruction(
    client: Client,
    sender: Keypair,
    recipient: PublicKey,
    amount: Any,
    commitment: Commitment | None,
) -> Instruction:
    sender_info, recipient_info = _account_infos(
        client, [sender.public_key, recipient], commitment
    )
    if sender_info is None:
        raise ValueError(f"Sender account not found: {sender.public_key}")
    _validate_system_account(sender_info, "Sender")
    if recipient_info is not None:
        _validate_system_account(recipient_info, "Recipient")

    lamports = sol_to_lamport(amount)
    if lamports > sender_info.lamports:
        raise ValueError("Insufficient sender balance")
    return transfer(sender.public_key, recipient, lamports)


def _create_token_instruction(
    client: Client,
    sender: Keypair,
    recipient: PublicKey,
    mint_address: PublicKey,
    amount: Any,
    memo: str | None,
    commitment: Commitment | None,
) -> Instruction:
    token_program, mint = _load_token_mint(client, mint_address, commitment)
    _validate_solana_pay_mint_for_creation(mint)

    sender_ata = get_associated_token_address(
        sender.public_key, mint_address, token_program
    )
    recipient_ata = get_associated_token_address(recipient, mint_address, token_program)
    sender_info, recipient_info = _account_infos(
        client, [sender_ata, recipient_ata], commitment
    )
    if sender_info is None:
        raise ValueError(f"Sender associated token account not found: {sender_ata}")
    if recipient_info is None:
        raise ValueError(
            f"Recipient associated token account not found: {recipient_ata}"
        )

    sender_account = _token_account(
        sender_info,
        token_program,
        expected_mint=mint_address,
        expected_owner=sender.public_key,
        role="Sender",
    )
    recipient_account = _token_account(
        recipient_info,
        token_program,
        expected_mint=mint_address,
        expected_owner=recipient,
        role="Recipient",
    )
    _validate_solana_pay_accounts(sender_account, recipient_account, memo)
    base_units = token_amount_to_base_units(amount, mint.decimals)
    if base_units > sender_account.amount:
        raise ValueError("Insufficient sender token balance")

    return transfer_checked(
        sender_ata,
        mint_address,
        recipient_ata,
        sender.public_key,
        base_units,
        mint.decimals,
        token_program_id=token_program,
        extensions=(mint, sender_account, recipient_account),
    )


def _load_token_mint(
    client: Client,
    mint_address: PublicKey,
    commitment: Commitment | None,
    *,
    expected_program: PublicKey | None = None,
) -> tuple[PublicKey, TokenMint]:
    """Load a mint and reject extensions with non-standard UI amount semantics."""

    mint_info = _account_info(client, mint_address, commitment)
    try:
        token_program = PublicKey(mint_info.owner)
    except (TypeError, ValueError) as error:
        raise ValueError("Token mint owner is invalid") from error
    if token_program not in TOKEN_PROGRAM_IDS:
        raise ValueError("Token mint is not owned by SPL Token or Token-2022")
    if expected_program is not None and token_program != expected_program:
        raise ValueError("Token mint owner does not match the transfer program")
    if mint_info.executable:
        raise ValueError("Token mint account must not be executable")

    mint = parse_mint(_account_data(mint_info), token_program)
    if not mint.is_initialized:
        raise ValueError("Token mint is not initialized")
    _validate_solana_pay_mint_extensions(mint)
    return token_program, mint


def _validate_solana_pay_mint_extensions(mint: TokenMint) -> None:
    for extension in mint.extensions:
        extension_type = extension.extension_type
        if extension_type is None:
            raise UnsupportedTokenExtensionError(
                f"unknown Token-2022 extension {extension.type_id} cannot be used "
                "for a Solana Pay transfer"
            )
        reason = _UNSUPPORTED_PAY_AMOUNT_EXTENSIONS.get(extension_type)
        if reason is not None:
            raise UnsupportedTokenExtensionError(reason)
        if extension_type == TokenExtensionType.NON_TRANSFERABLE:
            raise UnsupportedTokenExtensionError(
                "non-transferable mints cannot be used for payments"
            )


def _validate_solana_pay_mint_for_creation(mint: TokenMint) -> None:
    for extension in mint.extensions:
        extension_type = extension.extension_type
        if extension_type == TokenExtensionType.PAUSABLE:
            if len(extension.data) != 33 or extension.data[-1] not in (0, 1):
                raise ValueError("Token-2022 pausable mint extension is malformed")
            if extension.data[-1]:
                raise UnsupportedTokenExtensionError(
                    "paused Token-2022 mints cannot be transferred"
                )


def _validate_solana_pay_accounts(
    sender: TokenAccount,
    recipient: TokenAccount,
    memo: str | None,
) -> None:
    for account in (sender, recipient):
        for extension in account.extensions:
            if extension.extension_type is None:
                raise UnsupportedTokenExtensionError(
                    f"unknown Token-2022 extension {extension.type_id} cannot be "
                    "used for a Solana Pay transfer"
                )
            if extension.extension_type == TokenExtensionType.NON_TRANSFERABLE_ACCOUNT:
                raise UnsupportedTokenExtensionError(
                    "non-transferable token accounts cannot be used for payments"
                )

    for extension in recipient.extensions:
        if extension.extension_type == TokenExtensionType.MEMO_TRANSFER:
            if len(extension.data) != 1 or extension.data[0] not in (0, 1):
                raise ValueError("Token-2022 memo-transfer extension is malformed")
            if extension.data[0] and memo is None:
                raise UnsupportedTokenExtensionError(
                    "recipient token account requires a transfer memo"
                )


def _validate_system_account(account: AccountInfo, role: str) -> None:
    if account.owner != str(SYSTEM_PROGRAM_ID) or account.executable:
        raise ValueError(f"{role} must be a non-executable system account")


def _token_account(
    info: AccountInfo,
    token_program: PublicKey,
    *,
    expected_mint: PublicKey,
    expected_owner: PublicKey,
    role: str,
) -> TokenAccount:
    if info.owner != str(token_program) or info.executable:
        raise ValueError(f"{role} token account has an invalid program owner")
    account = parse_token_account(_account_data(info), token_program)
    if account.mint != expected_mint:
        raise ValueError(f"{role} token account has the wrong mint")
    if account.owner != expected_owner:
        raise ValueError(f"{role} token account has the wrong owner")
    if account.state == TokenAccountState.UNINITIALIZED:
        raise ValueError(f"{role} token account is not initialized")
    if account.state == TokenAccountState.FROZEN:
        raise ValueError(f"{role} token account is frozen")
    return account


def _account_data(info: AccountInfo) -> bytes:
    data = info.data
    if not (
        isinstance(data, list)
        and len(data) == 2
        and isinstance(data[0], str)
        and data[1] == "base64"
    ):
        raise ValueError("Account data is not base64 encoded")
    if len(data[0]) > (MAX_TOKEN_ACCOUNT_DATA_BYTES * 4 // 3) + 4:
        raise ValueError("Token account data is too large")
    try:
        decoded = base64.b64decode(data[0], validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Account data contains invalid base64") from error
    if len(decoded) > MAX_TOKEN_ACCOUNT_DATA_BYTES:
        raise ValueError("Token account data is too large")
    return decoded


def _references(
    references: Sequence[PublicKey] | PublicKey | None,
) -> list[PublicKey]:
    if references is None:
        return []
    values = (
        list(references)
        if isinstance(references, Sequence) and not isinstance(references, PublicKey)
        else [references]
    )
    if not all(isinstance(reference, PublicKey) for reference in values):
        raise ValueError("references must be PublicKey objects")
    return values


def _account_info(
    client: Client,
    public_key: PublicKey,
    commitment: Commitment | None,
) -> AccountInfo:
    response = client.get_account_info(public_key, commitment=commitment)
    if isinstance(response, AccountInfo):
        return response
    result = unwrap_rpc_response(response)
    if not isinstance(result, dict):
        raise ValueError("Account-info RPC response is malformed")
    value = result.get("value")
    if value is None:
        raise ValueError(f"Account not found: {public_key}")
    if not isinstance(value, dict):
        raise ValueError("Account-info RPC response is malformed")
    return AccountInfo(cast(AccountInfoType, value))


def _account_infos(
    client: Client,
    public_keys: list[PublicKey],
    commitment: Commitment | None,
) -> list[AccountInfo | None]:
    response = client.get_multiple_accounts(
        cast(list[PublicKey | str], public_keys),
        commitment=commitment,
        encoding="base64",
    )
    if isinstance(response, list):
        values = response
    else:
        value = unwrap_rpc_response(response)
        if isinstance(value, dict):
            value = value.get("value")
        if not isinstance(value, list):
            raise ValueError("Multiple-account RPC response is malformed")
        values = [AccountInfo(item) if item is not None else None for item in value]
    if len(values) != len(public_keys) or not all(
        value is None or isinstance(value, AccountInfo) for value in values
    ):
        raise ValueError("Multiple-account RPC response is malformed")
    return values
