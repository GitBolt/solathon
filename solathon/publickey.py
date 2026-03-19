from __future__ import annotations

import base58
from typing import List

class PublicKey:
    LENGTH = 32

    def __init__(self, value: bytes | int | str | List[int] | bytearray):
        if isinstance(value, str):
            try:
                self.byte_value = base58.b58decode(value)
            except ValueError:
                raise ValueError("Invalid public key")

        elif isinstance(value, int):
            self.byte_value = bytes([value])

        else:
            self.byte_value = bytes(value)

        if len(self.byte_value) != self.LENGTH:
            raise ValueError("Invalid public key, the length must be 32 bytes")

    def __bytes__(self) -> bytes:
        return (
            self.byte_value
            if len(self.byte_value) == self.LENGTH
            else self.byte_value.rjust(self.LENGTH, b"\0")
        )

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return self.base58_encode().decode("utf-8")
    
    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, PublicKey):
            return self.byte_value == __value.byte_value
        return False

    def __hash__(self) -> int:
        return hash(self.byte_value)

    def base58_encode(self) -> bytes:
        return base58.b58encode(bytes(self))