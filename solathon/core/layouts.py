from __future__ import annotations

from enum import IntEnum
from typing import Any

from ..publickey import PublicKey


class InstructionType(IntEnum):
    CREATE_ACCOUNT = 0
    ASSIGN = 1
    TRANSFER = 2
    CREATE_ACCOUNT_WITH_SEED = 3
    ADVANCE_NONCE_ACCOUNT = 4
    WITHDRAW_NONCE_ACCOUNT = 5
    INITIALIZE_NONCE_ACCOUNT = 6
    AUTHORIZE_NONCE_ACCOUNT = 7
    ALLOCATE = 8
    ALLOCATE_WITH_SEED = 9
    ASSIGN_WITH_SEED = 10
    TRANSFER_WITH_SEED = 11
    UPGRADE_NONCE_ACCOUNT = 12
    CREATE_ACCOUNT_ALLOW_PREFUND = 13


SYSTEM_PROGRAM_ID = PublicKey("11111111111111111111111111111111")
SYSVAR_RECENT_BLOCKHASHES_ID = PublicKey("SysvarRecentB1ockHashes11111111111111111111")
SYSVAR_RENT_ID = PublicKey("SysvarRent111111111111111111111111111111111")


def encode_u32(value: int, field: str = "value") -> bytes:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field} must be an integer")
    if not 0 <= value < 2**32:
        raise ValueError(f"{field} must fit in an unsigned 32-bit integer")
    return value.to_bytes(4, "little")


def encode_u64(value: int, field: str = "value") -> bytes:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field} must be an integer")
    if not 0 <= value < 2**64:
        raise ValueError(f"{field} must fit in an unsigned 64-bit integer")
    return value.to_bytes(8, "little")


def encode_string(value: str, field: str = "value") -> bytes:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    encoded = value.encode("utf-8")
    return encode_u64(len(encoded), f"{field} length") + encoded


def encode_system_instruction(instruction: InstructionType, **values: Any) -> bytes:
    data = bytearray(encode_u32(int(instruction), "instruction"))

    if instruction == InstructionType.CREATE_ACCOUNT:
        data.extend(encode_u64(values["lamports"], "lamports"))
        data.extend(encode_u64(values["space"], "space"))
        data.extend(bytes(values["program_id"]))
    elif instruction == InstructionType.ASSIGN:
        data.extend(bytes(values["program_id"]))
    elif instruction == InstructionType.TRANSFER:
        data.extend(encode_u64(values["lamports"], "lamports"))
    elif instruction == InstructionType.CREATE_ACCOUNT_WITH_SEED:
        data.extend(bytes(values["base"]))
        data.extend(encode_string(values["seed"], "seed"))
        data.extend(encode_u64(values["lamports"], "lamports"))
        data.extend(encode_u64(values["space"], "space"))
        data.extend(bytes(values["program_id"]))
    elif instruction == InstructionType.WITHDRAW_NONCE_ACCOUNT:
        data.extend(encode_u64(values["lamports"], "lamports"))
    elif instruction in {
        InstructionType.INITIALIZE_NONCE_ACCOUNT,
        InstructionType.AUTHORIZE_NONCE_ACCOUNT,
    }:
        data.extend(bytes(values["authorized"]))
    elif instruction == InstructionType.ALLOCATE:
        data.extend(encode_u64(values["space"], "space"))
    elif instruction == InstructionType.ALLOCATE_WITH_SEED:
        data.extend(bytes(values["base"]))
        data.extend(encode_string(values["seed"], "seed"))
        data.extend(encode_u64(values["space"], "space"))
        data.extend(bytes(values["program_id"]))
    elif instruction == InstructionType.ASSIGN_WITH_SEED:
        data.extend(bytes(values["base"]))
        data.extend(encode_string(values["seed"], "seed"))
        data.extend(bytes(values["program_id"]))
    elif instruction == InstructionType.TRANSFER_WITH_SEED:
        data.extend(encode_u64(values["lamports"], "lamports"))
        data.extend(encode_string(values["from_seed"], "from_seed"))
        data.extend(bytes(values["from_owner"]))
    elif instruction == InstructionType.CREATE_ACCOUNT_ALLOW_PREFUND:
        # When no payer is supplied, the destination must already contain the
        # required lamports and the wire funding amount is zero.
        data.extend(encode_u64(values["lamports"], "lamports"))
        data.extend(encode_u64(values["space"], "space"))
        data.extend(bytes(values["program_id"]))

    return bytes(data)
