from __future__ import annotations

from collections.abc import Sequence

import base58
from solders.pubkey import Pubkey


class PublicKey:
    """A Solana public key backed by the native ``solders`` implementation."""

    LENGTH = Pubkey.LENGTH
    MAX_SEED_LENGTH = 32
    MAX_SEEDS = 16

    __slots__ = ("_value",)

    def __init__(
        self,
        value: bytes | bytearray | memoryview | int | str | Sequence[int] | Pubkey,
    ) -> None:
        if isinstance(value, bool):
            raise TypeError("Public key cannot be a boolean")
        try:
            if isinstance(value, Pubkey):
                self._value = value
            elif isinstance(value, str):
                self._value = Pubkey.from_string(value)
            elif isinstance(value, int):
                if not 0 <= value < 2 ** (self.LENGTH * 8):
                    raise ValueError("Public key integer is out of range")
                self._value = Pubkey.from_bytes(value.to_bytes(self.LENGTH, "big"))
            else:
                raw = bytes(value)
                if len(raw) != self.LENGTH:
                    raise ValueError(
                        f"Invalid public key: expected {self.LENGTH} bytes, got {len(raw)}"
                    )
                self._value = Pubkey.from_bytes(raw)
        except (TypeError, ValueError) as error:
            if isinstance(error, ValueError) and (
                "out of range" in str(error) or "expected" in str(error)
            ):
                raise
            raise ValueError("Invalid public key") from error

    @property
    def byte_value(self) -> bytes:
        """The immutable 32-byte public-key value."""

        return bytes(self._value)

    def to_solders(self) -> Pubkey:
        """Return the native ``solders.pubkey.Pubkey`` value without copying."""

        return self._value

    @classmethod
    def from_solders(cls, value: Pubkey) -> PublicKey:
        return cls(value)

    def __bytes__(self) -> bytes:
        return bytes(self._value)

    def __repr__(self) -> str:
        return f"PublicKey('{self}')"

    def __str__(self) -> str:
        return str(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PublicKey):
            return self._value == other._value
        if isinstance(other, Pubkey):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def base58_encode(self) -> bytes:
        """Return the base58 representation as bytes for backward compatibility."""

        return base58.b58encode(bytes(self._value))

    def is_on_curve(self) -> bool:
        return self._value.is_on_curve()

    @classmethod
    def create_with_seed(
        cls,
        base_public_key: PublicKey,
        seed: str,
        program_id: PublicKey,
    ) -> PublicKey:
        if not isinstance(base_public_key, PublicKey) or not isinstance(
            program_id, PublicKey
        ):
            raise TypeError("base_public_key and program_id must be PublicKey objects")
        if not isinstance(seed, str):
            raise TypeError("seed must be a string")
        if len(seed.encode("utf-8")) > cls.MAX_SEED_LENGTH:
            raise ValueError("Seed length cannot exceed 32 bytes")
        return cls(
            Pubkey.create_with_seed(
                base_public_key.to_solders(), seed, program_id.to_solders()
            )
        )

    @classmethod
    def create_program_address(
        cls,
        seeds: Sequence[bytes | bytearray | memoryview],
        program_id: PublicKey,
    ) -> PublicKey:
        if not isinstance(program_id, PublicKey):
            raise TypeError("program_id must be a PublicKey")
        normalized = cls._validate_seeds(seeds)
        try:
            return cls(
                Pubkey.create_program_address(normalized, program_id.to_solders())
            )
        except Exception as error:
            raise ValueError(str(error)) from error

    @classmethod
    def find_program_address(
        cls,
        seeds: Sequence[bytes | bytearray | memoryview],
        program_id: PublicKey,
    ) -> tuple[PublicKey, int]:
        if not isinstance(program_id, PublicKey):
            raise TypeError("program_id must be a PublicKey")
        normalized = cls._validate_seeds(seeds)
        # ``find_program_address`` appends the bump as one additional seed.
        # Reject sixteen caller-provided seeds before entering solders, whose
        # native implementation otherwise raises an uncatchable panic.
        if len(normalized) >= cls.MAX_SEEDS:
            raise ValueError("A program address search can use at most 15 seeds")
        public_key, bump = Pubkey.find_program_address(
            normalized, program_id.to_solders()
        )
        return cls(public_key), bump

    @classmethod
    def _validate_seeds(
        cls, seeds: Sequence[bytes | bytearray | memoryview]
    ) -> list[bytes]:
        if isinstance(seeds, (bytes, bytearray, str)):
            raise TypeError("seeds must be a sequence of byte strings")
        normalized = []
        for seed in seeds:
            if not isinstance(seed, (bytes, bytearray, memoryview)):
                raise TypeError("each seed must be bytes-like")
            normalized.append(bytes(seed))
        if len(normalized) > cls.MAX_SEEDS:
            raise ValueError("A program address can use at most 16 seeds")
        if any(len(seed) > cls.MAX_SEED_LENGTH for seed in normalized):
            raise ValueError("Seed length cannot exceed 32 bytes")
        return normalized


PublicKeyLike = PublicKey | Pubkey | str | bytes
