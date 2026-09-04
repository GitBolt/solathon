from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from base58 import b58decode

from ..client import Client
from ..core.instructions import MEMO_PROGRAM_ID
from ..core.layouts import SYSTEM_PROGRAM_ID, InstructionType
from ..core.types import Commitment
from ..core.types.block import Message as TransactionMessage
from ..core.types.block import TransactionElement
from ..publickey import PublicKey
from ..token import (
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_IDS,
    get_associated_token_address,
    token_amount_to_base_units,
)
from ..utils import sol_to_lamport, unwrap_rpc_response
from .create_transfer import _load_token_mint
from .types import CreateTransferFields


def validate_transfer(
    client: Client,
    signature: str,
    transfer_fields: CreateTransferFields,
    commitment: Commitment | None = "confirmed",
    *,
    max_supported_transaction_version: int | None = 0,
) -> TransactionElement:
    """Validate a confirmed SOL, SPL Token, or Token-2022 Pay transfer.

    Validation is structural *and* economic: the requested transfer must be the
    final top-level instruction and the recipient's net balance increase must
    be at least the requested amount. A requested memo must be immediately
    before the transfer.
    """

    recipient = transfer_fields.get("recipient")
    amount = transfer_fields.get("amount")
    if not isinstance(recipient, PublicKey):
        raise ValueError("recipient must be a PublicKey")
    if amount is None:
        raise ValueError("amount is required")
    mint = transfer_fields.get("spl_token")
    if mint is not None and not isinstance(mint, PublicKey):
        raise ValueError("spl_token must be a PublicKey")

    response = client.get_transaction(
        signature,
        commitment=commitment,
        max_supported_transaction_version=max_supported_transaction_version,
    )
    if response is None:
        raise ValueError("Transaction not found")
    if isinstance(response, dict):
        value = unwrap_rpc_response(cast(Any, response))
        if value is None:
            raise ValueError("Transaction not found")
        response = TransactionElement(value)
    if response.meta is None:
        raise ValueError("Transaction metadata is missing")
    if response.meta.err is not None:
        raise ValueError(f"Transaction failed: {response.meta.err}")

    message = response.transaction.message
    if not message.instructions:
        raise ValueError("Transaction is missing the transfer instruction")
    static_keys = [
        key if isinstance(key, PublicKey) else PublicKey(key)
        for key in message.account_keys
    ]
    writable_loaded = [
        PublicKey(address) for address in response.meta.loaded_writable_addresses
    ]
    readonly_loaded = [
        PublicKey(address) for address in response.meta.loaded_readonly_addresses
    ]
    account_keys = [*static_keys, *writable_loaded, *readonly_loaded]

    instruction = message.instructions[-1]
    instruction_accounts = _account_indexes(instruction.accounts, len(account_keys))
    program_index = instruction.program_id_index
    if (
        not isinstance(program_index, int)
        or isinstance(program_index, bool)
        or not 0 <= program_index < len(account_keys)
    ):
        raise ValueError("Transfer instruction has an invalid program index")
    program_id = account_keys[program_index]
    data = _instruction_data(instruction.data)

    if mint is None:
        recipient_index, reference_indexes, expected_base_units = (
            _validate_native_instruction(
                message,
                account_keys,
                instruction_accounts,
                data,
                recipient,
                amount,
                program_id,
                len(static_keys),
                len(writable_loaded),
            )
        )
        _validate_native_balance(response.meta, recipient_index, expected_base_units)
    else:
        mint_decimals = None
        if program_id == TOKEN_2022_PROGRAM_ID:
            _, mint_state = _load_token_mint(
                client,
                mint,
                commitment,
                expected_program=program_id,
            )
            mint_decimals = mint_state.decimals
        recipient_index, reference_indexes, expected_base_units = (
            _validate_token_instruction(
                message,
                account_keys,
                instruction_accounts,
                data,
                recipient,
                mint,
                amount,
                program_id,
                response.meta,
                len(static_keys),
                len(writable_loaded),
                mint_decimals,
            )
        )

    reference_list = _references(transfer_fields.get("reference"))
    actual_references = [account_keys[index] for index in reference_indexes]
    if actual_references != reference_list:
        raise ValueError("Transfer references do not match the request")
    for index in reference_indexes:
        if _is_signer(message, index, len(static_keys)) or _is_writable(
            message, index, len(static_keys), len(writable_loaded)
        ):
            raise ValueError("Transfer references must be read-only non-signers")

    memo = transfer_fields.get("memo")
    if memo is not None:
        if not isinstance(memo, str):
            raise TypeError("memo must be a string")
        if len(message.instructions) < 2:
            raise ValueError("Transaction is missing the requested memo")
        memo_instruction = message.instructions[-2]
        if (
            not isinstance(memo_instruction.program_id_index, int)
            or isinstance(memo_instruction.program_id_index, bool)
            or not 0 <= memo_instruction.program_id_index < len(account_keys)
        ):
            raise ValueError("Memo instruction has an invalid program index")
        if account_keys[memo_instruction.program_id_index] != MEMO_PROGRAM_ID:
            raise ValueError("Memo is not immediately before the transfer")
        try:
            memo_data = _instruction_data(memo_instruction.data)
        except ValueError as error:
            raise ValueError("Memo instruction contains invalid data") from error
        if memo_data != memo.encode("utf-8"):
            raise ValueError("Memo does not match the request")

    return response


def _validate_native_instruction(
    message: TransactionMessage,
    account_keys: list[PublicKey],
    accounts: list[int],
    data: bytes,
    recipient: PublicKey,
    amount,
    program_id: PublicKey,
    static_count: int,
    loaded_writable_count: int,
) -> tuple[int, list[int], int]:
    if program_id != SYSTEM_PROGRAM_ID or len(data) != 12:
        raise ValueError("Final instruction is not a system transfer")
    instruction_type = int.from_bytes(data[:4], "little")
    if instruction_type != InstructionType.TRANSFER or len(accounts) < 2:
        raise ValueError("Final instruction is not a system transfer")

    expected = sol_to_lamport(amount)
    transferred = int.from_bytes(data[4:], "little")
    if transferred != expected:
        raise ValueError("Transfer instruction amount does not match the request")

    source_index, recipient_index, *references = accounts
    if account_keys[recipient_index] != recipient:
        raise ValueError("Transfer recipient does not match the request")
    _validate_transfer_roles(
        message,
        source_index,
        recipient_index,
        source_index,
        static_count,
        loaded_writable_count,
    )
    return recipient_index, references, expected


def _validate_token_instruction(
    message: TransactionMessage,
    account_keys: list[PublicKey],
    accounts: list[int],
    data: bytes,
    recipient: PublicKey,
    mint: PublicKey,
    amount,
    program_id: PublicKey,
    meta,
    static_count: int,
    loaded_writable_count: int,
    mint_decimals: int | None,
) -> tuple[int, list[int], int]:
    if program_id not in TOKEN_PROGRAM_IDS or not data:
        raise ValueError("Final instruction is not a token transfer")

    instruction_type = data[0]
    if instruction_type == 12:  # TransferChecked
        if len(data) != 10 or len(accounts) < 4:
            raise ValueError("Final instruction is not a checked token transfer")
        source_index, mint_index, recipient_index, authority_index, *references = (
            accounts
        )
        if account_keys[mint_index] != mint:
            raise ValueError("Transfer mint does not match the request")
        instruction_decimals = data[9]
    elif instruction_type == 3:  # Transfer
        if len(data) != 9 or len(accounts) < 3:
            raise ValueError("Final instruction is not a token transfer")
        source_index, recipient_index, authority_index, *references = accounts
        instruction_decimals = None
    else:
        raise ValueError("Final instruction is not a token transfer")

    recipient_ata = get_associated_token_address(recipient, mint, program_id)
    if account_keys[recipient_index] != recipient_ata:
        raise ValueError("Transfer destination is not the recipient token account")
    _validate_transfer_roles(
        message,
        source_index,
        recipient_index,
        authority_index,
        static_count,
        loaded_writable_count,
    )

    pre, post, decimals = _token_balance_change(
        meta, recipient_index, recipient, mint, program_id
    )
    if mint_decimals is not None and decimals != mint_decimals:
        raise ValueError("Token balance decimals do not match the mint")
    if instruction_decimals is not None and instruction_decimals != decimals:
        raise ValueError("Transfer decimals do not match the token balance")
    expected = token_amount_to_base_units(amount, decimals)
    transferred = int.from_bytes(data[1:9], "little")
    if transferred != expected:
        raise ValueError("Transfer instruction amount does not match the request")
    if post - pre < expected:
        raise ValueError("Recipient did not receive the requested token amount")
    return recipient_index, references, expected


def _validate_transfer_roles(
    message: TransactionMessage,
    source_index: int,
    recipient_index: int,
    authority_index: int,
    static_count: int,
    loaded_writable_count: int,
) -> None:
    if not _is_signer(message, authority_index, static_count):
        raise ValueError("Transfer authority is not a signer")
    if not _is_writable(message, source_index, static_count, loaded_writable_count):
        raise ValueError("Transfer source is not writable")
    if not _is_writable(message, recipient_index, static_count, loaded_writable_count):
        raise ValueError("Transfer recipient is not writable")


def _validate_native_balance(meta, recipient_index: int, expected: int) -> None:
    if recipient_index >= len(meta.pre_balances) or recipient_index >= len(
        meta.post_balances
    ):
        raise ValueError("Transaction metadata is missing recipient balances")
    if (
        meta.post_balances[recipient_index] - meta.pre_balances[recipient_index]
        < expected
    ):
        raise ValueError("Recipient did not receive the requested amount")


def _token_balance_change(
    meta,
    account_index: int,
    recipient: PublicKey,
    mint: PublicKey,
    program_id: PublicKey,
) -> tuple[int, int, int]:
    pre = _token_balance(meta.pre_token_balances, account_index, "pre")
    post = _token_balance(meta.post_token_balances, account_index, "post")
    for balance in (pre, post):
        if balance.get("mint") != str(mint):
            raise ValueError("Recipient token balance has the wrong mint")
        balance_program = balance.get("programId")
        if balance_program is not None and balance_program != str(program_id):
            raise ValueError("Recipient token balance has the wrong token program")
        balance_owner = balance.get("owner")
        if balance_owner is not None and balance_owner != str(recipient):
            raise ValueError("Recipient token balance has the wrong owner")
    pre_amount, pre_decimals = _token_balance_amount(pre)
    post_amount, post_decimals = _token_balance_amount(post)
    if pre_decimals != post_decimals:
        raise ValueError("Recipient token balance decimals changed")
    return pre_amount, post_amount, pre_decimals


def _token_balance(balances, account_index: int, position: str) -> dict:
    if not isinstance(balances, list):
        raise ValueError(f"Transaction metadata is missing {position} token balances")
    matches = [
        balance
        for balance in balances
        if isinstance(balance, dict)
        and isinstance(balance.get("accountIndex"), int)
        and not isinstance(balance.get("accountIndex"), bool)
        and balance.get("accountIndex") == account_index
    ]
    if len(matches) != 1:
        raise ValueError(f"Transaction metadata has no unique {position} token balance")
    return matches[0]


def _token_balance_amount(balance: dict) -> tuple[int, int]:
    value = balance.get("uiTokenAmount")
    if not isinstance(value, dict):
        raise ValueError("Transaction token balance is malformed")
    amount = value.get("amount")
    decimals = value.get("decimals")
    if (
        not isinstance(amount, str)
        or not amount.isascii()
        or not amount.isdigit()
        or not isinstance(decimals, int)
        or isinstance(decimals, bool)
        or not 0 <= decimals <= 255
    ):
        raise ValueError("Transaction token balance is malformed")
    return int(amount), decimals


def _account_indexes(accounts, account_count: int) -> list[int]:
    if not isinstance(accounts, list) or any(
        not isinstance(index, int)
        or isinstance(index, bool)
        or not 0 <= index < account_count
        for index in accounts
    ):
        raise ValueError("Transfer instruction has invalid account indexes")
    return list(accounts)


def _instruction_data(value) -> bytes:
    if not isinstance(value, (str, bytes)):
        raise ValueError("Transfer instruction contains invalid data")
    try:
        return b58decode(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Transfer instruction contains invalid data") from error


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


def _is_signer(message: TransactionMessage, index: int, static_count: int) -> bool:
    return index < static_count and message.is_account_signer(index)


def _is_writable(
    message: TransactionMessage,
    index: int,
    static_count: int,
    loaded_writable_count: int,
) -> bool:
    if index < static_count:
        return message.is_account_writable(index)
    return index < static_count + loaded_writable_count
