from __future__ import annotations

from enum import IntEnum
from struct import pack
from typing import Any, Callable

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


SYSTEM_PROGRAM_ID: PublicKey = PublicKey("11111111111111111111111111111111")


class Layout:
    """Small encoder with the same build interface used by instruction helpers."""

    def __init__(self, encoder: Callable[[Any], bytes]) -> None:
        self.encoder = encoder

    def build(self, value: Any) -> bytes:
        """Encodes a layout value into its wire representation."""
        return self.encoder(value)


def _encode_public_key(value: bytes) -> bytes:
    """Encodes and validates a public key."""
    public_key = bytes(value)
    if len(public_key) != PublicKey.LENGTH:
        raise ValueError("Public key must contain 32 bytes")
    return public_key


def _encode_rust_string(value: str) -> bytes:
    """Encodes a string using Solana's eight-byte length prefix."""
    encoded = value.encode("utf-8")
    return pack("<Q", len(encoded)) + encoded


PUBLIC_KEY_LAYOUT = Layout(_encode_public_key)
RUST_STRING_LAYOUT = Layout(_encode_rust_string)

CREATE_ACCOUNT_LAYOUT = Layout(
    lambda args: pack("<QQ", args["lamports"], args["space"])
    + _encode_public_key(args["program_id"])
)
ASSIGN_LAYOUT = Layout(lambda args: _encode_public_key(args["program_id"]))
TRANFER_LAYOUT = Layout(lambda args: pack("<Q", args["lamports"]))
CREATE_ACCOUNT_WTIH_SEED_LAYOUT = Layout(
    lambda args: _encode_public_key(args["base"])
    + _encode_rust_string(args["seed"])
    + pack("<QQ", args["lamports"], args["space"])
    + _encode_public_key(args["program_id"])
)
WITHDRAW_NONCE_ACCOUNT_LAYOUT = Layout(lambda args: pack("<Q", args["lamports"]))
INITIALIZE_NONCE_ACCOUNT_LAYOUT = Layout(
    lambda args: _encode_public_key(args["authorized"])
)
AUTHORIZE_NONCE_ACCOUNT_LAYOUT = Layout(
    lambda args: _encode_public_key(args["authorized"])
)
ALLOCATE_LAYOUT = Layout(lambda args: pack("<Q", args["space"]))
ALLOCATE_WITH_SEED_LAYOUT = Layout(
    lambda args: _encode_public_key(args["base"])
    + _encode_rust_string(args["seed"])
    + pack("<Q", args["space"])
    + _encode_public_key(args["program_id"])
)
ASSIGN_WITH_SEED_LAYOUT = Layout(
    lambda args: _encode_public_key(args["base"])
    + _encode_rust_string(args["seed"])
    + _encode_public_key(args["program_id"])
)
TRANSFER_WITH_SEED_LAYOUT = Layout(
    lambda args: pack("<Q", args["lamports"])
    + _encode_rust_string(args["from_seed"])
    + _encode_public_key(args.get("from_owner", args.get("from_ower")))
)

INSTRUCTION_LAYOUTS = {
    InstructionType.CREATE_ACCOUNT: CREATE_ACCOUNT_LAYOUT,
    InstructionType.ASSIGN: ASSIGN_LAYOUT,
    InstructionType.TRANSFER: TRANFER_LAYOUT,
    InstructionType.CREATE_ACCOUNT_WITH_SEED: CREATE_ACCOUNT_WTIH_SEED_LAYOUT,
    InstructionType.WITHDRAW_NONCE_ACCOUNT: WITHDRAW_NONCE_ACCOUNT_LAYOUT,
    InstructionType.INITIALIZE_NONCE_ACCOUNT: INITIALIZE_NONCE_ACCOUNT_LAYOUT,
    InstructionType.AUTHORIZE_NONCE_ACCOUNT: AUTHORIZE_NONCE_ACCOUNT_LAYOUT,
    InstructionType.ALLOCATE: ALLOCATE_LAYOUT,
    InstructionType.ALLOCATE_WITH_SEED: ALLOCATE_WITH_SEED_LAYOUT,
    InstructionType.ASSIGN_WITH_SEED: ASSIGN_WITH_SEED_LAYOUT,
    InstructionType.TRANSFER_WITH_SEED: TRANSFER_WITH_SEED_LAYOUT,
}


def _encode_instruction(value: dict[str, Any]) -> bytes:
    """Encodes a system instruction discriminator and arguments."""
    instruction_type = InstructionType(value["type"])
    data = pack("<I", instruction_type)
    if instruction_type == InstructionType.ADVANCE_NONCE_ACCOUNT:
        return data
    return data + INSTRUCTION_LAYOUTS[instruction_type].build(value["args"])


SYSTEM_INSTRUCTIONS_LAYOUT = Layout(_encode_instruction)
