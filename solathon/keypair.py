from __future__ import annotations

import json
from pathlib import Path

import base58
from nacl.public import PrivateKey as NaclPrivateKey
from nacl.signing import SignedMessage, SigningKey
from solders.keypair import Keypair as SoldersKeypair

from .publickey import PublicKey


class PrivateKey:
    """Immutable 64-byte Solana keypair material (seed + public key)."""

    LENGTH = 64

    __slots__ = ("_byte_value",)

    def __init__(self, value: bytes | bytearray | memoryview) -> None:
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise TypeError("Private key must be bytes-like")
        raw = bytes(value)
        if len(raw) != self.LENGTH:
            raise ValueError("Private key must contain 64 bytes")
        self._byte_value = raw

    @property
    def byte_value(self) -> bytes:
        return self._byte_value

    def __bytes__(self) -> bytes:
        return self._byte_value

    def __str__(self) -> str:
        return "<redacted>"

    def __repr__(self) -> str:
        return "PrivateKey(<redacted>)"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PrivateKey):
            return self._byte_value == other._byte_value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._byte_value)

    def base58_encode(self) -> bytes:
        return base58.b58encode(self._byte_value)


class Keypair:
    def __init__(
        self,
        value: SigningKey | NaclPrivateKey | SoldersKeypair | bytes | None = None,
    ) -> None:
        if value is None:
            self.key_pair = SigningKey.generate()
        elif isinstance(value, SigningKey):
            self.key_pair = value
        elif isinstance(value, NaclPrivateKey):
            self.key_pair = SigningKey(bytes(value))
        elif isinstance(value, SoldersKeypair):
            self.key_pair = SigningKey(value.secret())
        elif isinstance(value, bytes) and len(value) == 32:
            self.key_pair = SigningKey(value)
        else:
            raise ValueError(
                "Keypair initialization value must be a 32-byte seed or a "
                "PyNaCl or solders keypair object"
            )
        verify_key = bytes(self.key_pair.verify_key)
        self.public_key = PublicKey(verify_key)
        self.private_key = PrivateKey(bytes(self.key_pair) + verify_key)

    def sign(self, message: str | bytes) -> SignedMessage:
        if isinstance(message, str):
            message = message.encode("utf-8")

        if isinstance(message, bytes):
            return self.key_pair.sign(message)

        raise TypeError("Message argument must be either string or bytes")

    def __bytes__(self) -> bytes:
        """Return the canonical 64-byte Solana keypair representation."""

        return bytes(self.private_key)

    def to_solders(self) -> SoldersKeypair:
        """Return an equivalent native solders keypair."""

        return SoldersKeypair.from_bytes(bytes(self))

    @classmethod
    def from_solders(cls, value: SoldersKeypair) -> Keypair:
        if not isinstance(value, SoldersKeypair):
            raise TypeError("value must be a solders Keypair")
        return cls(value)

    @classmethod
    def from_seed(cls, seed: bytes | bytearray | memoryview) -> Keypair:
        """Create a keypair from an Ed25519 32-byte seed."""

        if not isinstance(seed, (bytes, bytearray, memoryview)):
            raise TypeError("Keypair seed must be bytes-like")
        raw = bytes(seed)
        if len(raw) != 32:
            raise ValueError("Keypair seed must contain 32 bytes")
        return cls(raw)

    @classmethod
    def from_private_key(
        cls,
        private_key: str | list[int] | bytes | bytearray,
    ) -> Keypair:
        if isinstance(private_key, list):
            try:
                private_key = bytes(private_key)
            except (TypeError, ValueError) as error:
                raise ValueError("Private key list must contain byte values") from error
        elif isinstance(private_key, str):
            try:
                private_key = base58.b58decode(private_key)
            except ValueError as error:
                raise ValueError("Private key must be valid base58") from error
        elif isinstance(private_key, bytearray):
            private_key = bytes(private_key)
        elif not isinstance(private_key, bytes):
            raise TypeError("Private key must be base58 text or a byte sequence")

        if len(private_key) not in (32, 64):
            raise ValueError("Private key must contain 32 or 64 bytes")
        seed = private_key[:32]
        keypair = cls(seed)
        if len(private_key) == 64 and private_key[32:] != bytes(keypair.public_key):
            raise ValueError("Private key public-key bytes do not match its seed")
        return keypair

    @classmethod
    def from_file(cls, file_path: str | Path) -> Keypair:
        with Path(file_path).expanduser().open(encoding="utf-8") as keypair_file:
            data = json.load(keypair_file)

        if not isinstance(data, list):
            raise ValueError("Keypair file must contain a JSON byte array")
        return cls.from_private_key(data)
