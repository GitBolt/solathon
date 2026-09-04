from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple

from base58 import b58decode, b58encode
from solders.hash import Hash
from solders.instruction import CompiledInstruction as SoldersCompiledInstruction
from solders.message import Message as SoldersMessage

from ..publickey import PublicKey

PUBLIC_KEY_LENGTH = 32


def decode_length(values: list[int]) -> int:
    length = 0
    for position in range(5):
        if not values:
            raise ValueError("Short vector ended before its length was decoded")
        byte = values.pop(0)
        length |= (byte & 0x7F) << (position * 7)
        if byte & 0x80 == 0:
            if position == 4 and byte > 0x0F:
                raise ValueError("Short vector length exceeds 32 bits")
            return length
    raise ValueError("Short vector length exceeds 32 bits")


def encode_length(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("Short vector length must be an integer")
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("Short vector length must fit in 32 bits")

    encoded = bytearray()
    remaining = value
    while True:
        byte = remaining & 0x7F
        remaining >>= 7
        encoded.append(byte | (0x80 if remaining else 0))
        if not remaining:
            return bytes(encoded)


def to_uint8_bytes(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("Value must be an integer")
    if not 0 <= value <= 255:
        raise ValueError("Value must fit in one byte")
    return bytes([value])


class CompiledInstruction(NamedTuple):
    accounts: bytes | list[int]
    program_id_index: int
    data: bytes


class MessageHeader(NamedTuple):
    num_required_signatures: int
    num_readonly_signed_accounts: int
    num_readonly_unsigned_accounts: int


class Message:
    def __init__(
        self,
        header: MessageHeader,
        account_keys: Sequence[PublicKey | str | bytes],
        instructions: list[CompiledInstruction],
        recent_blockhash: str,
    ):
        self.header = header
        self.account_keys = [
            PublicKey(bytes(key)) if isinstance(key, PublicKey) else PublicKey(key)
            for key in account_keys
        ]
        self.recent_blockhash = recent_blockhash
        self.instructions = instructions

    def encode_message(self) -> bytes:
        recent_blockhash = b58decode(self.recent_blockhash)
        if len(recent_blockhash) != PUBLIC_KEY_LENGTH:
            raise ValueError("Recent blockhash must decode to 32 bytes")
        return b"".join(
            [
                to_uint8_bytes(self.header.num_required_signatures),
                to_uint8_bytes(self.header.num_readonly_signed_accounts),
                to_uint8_bytes(self.header.num_readonly_unsigned_accounts),
                encode_length(len(self.account_keys)),
                b"".join(bytes(public_key) for public_key in self.account_keys),
                recent_blockhash,
            ]
        )

    @staticmethod
    def encode_instruction(instruction: CompiledInstruction) -> bytes:
        accounts = bytes(instruction.accounts)
        data = b58decode(instruction.data)
        return b"".join(
            [
                to_uint8_bytes(instruction.program_id_index),
                encode_length(len(accounts)),
                accounts,
                encode_length(len(data)),
                data,
            ]
        )

    def is_account_signer(self, index: int) -> bool:
        if not 0 <= index < len(self.account_keys):
            raise IndexError("Account index is outside the message")
        return index < self.header.num_required_signatures

    def is_account_writable(self, index: int) -> bool:
        if not 0 <= index < len(self.account_keys):
            raise IndexError("Account index is outside the message")
        writable_signer_count = (
            self.header.num_required_signatures
            - self.header.num_readonly_signed_accounts
        )
        writable_unsigned_limit = (
            len(self.account_keys) - self.header.num_readonly_unsigned_accounts
        )
        return index < writable_signer_count or (
            self.header.num_required_signatures <= index < writable_unsigned_limit
        )

    def serialize(self) -> bytes:
        return bytes(self.to_solders())

    def to_solders(self) -> SoldersMessage:
        """Convert to the native representation used for wire serialization."""

        return SoldersMessage.new_with_compiled_instructions(
            self.header.num_required_signatures,
            self.header.num_readonly_signed_accounts,
            self.header.num_readonly_unsigned_accounts,
            [public_key.to_solders() for public_key in self.account_keys],
            Hash.from_string(self.recent_blockhash),
            [
                SoldersCompiledInstruction(
                    instruction.program_id_index,
                    b58decode(instruction.data),
                    bytes(instruction.accounts),
                )
                for instruction in self.instructions
            ],
        )

    @classmethod
    def from_solders(cls, message: SoldersMessage) -> Message:
        return cls(
            MessageHeader(
                message.header.num_required_signatures,
                message.header.num_readonly_signed_accounts,
                message.header.num_readonly_unsigned_accounts,
            ),
            [PublicKey.from_solders(key) for key in message.account_keys],
            [
                CompiledInstruction(
                    accounts=bytes(instruction.accounts),
                    program_id_index=instruction.program_id_index,
                    data=b58encode(bytes(instruction.data)),
                )
                for instruction in message.instructions
            ],
            str(message.recent_blockhash),
        )

    @classmethod
    def from_buffer(cls, buffer: bytes) -> Message:
        if not isinstance(buffer, bytes):
            raise TypeError("Message buffer must be bytes")
        if not buffer:
            raise ValueError("Message buffer is empty")
        if buffer[0] & 0x80:
            raise ValueError("Versioned messages must be deserialized separately")
        return cls.from_solders(SoldersMessage.from_bytes(buffer))
