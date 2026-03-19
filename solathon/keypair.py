from __future__ import annotations

import json
import base58
from typing import List
from .publickey import PublicKey
from nacl.signing import SigningKey, SignedMessage
from nacl.public import PrivateKey as NaclPrivateKey


class PrivateKey(PublicKey):
    LENGTH = 64


class Keypair:

    def __init__(self, value: NaclPrivateKey | None = None) -> None:
        if value is None:
            self.key_pair = NaclPrivateKey.generate()
        elif isinstance(value, NaclPrivateKey):
            self.key_pair = value
        else:
            raise ValueError(
                "Keypair initialization value must be a "
                "nacl.public.PrivateKey object. To initialize with "
                "private key string, use 'from_private_key' method"
            )
        verify_key: bytes = bytes(
                            SigningKey(bytes(self.key_pair)).verify_key
                            )
        self.public_key = PublicKey(verify_key)
        self.private_key = PrivateKey(
            bytes(self.key_pair) + bytes(self.public_key)
        )

    def sign(self, message: str | bytes) -> SignedMessage:
        if isinstance(message, str):
            signing_key = SigningKey(bytes(self.key_pair))
            return signing_key.sign(bytes(message, encoding="utf-8"))

        if isinstance(message, bytes):
            signing_key = SigningKey(bytes(self.key_pair))
            return signing_key.sign(message)

        raise ValueError(
            "Message argument must be either string or bytes"
        )

    @classmethod
    def from_private_key(cls, private_key: str | List[int]) -> Keypair:
        if isinstance(private_key, list):
            private_key = bytes(private_key)
        elif isinstance(private_key, str):
            private_key = private_key.encode('utf-8')
            try:
                private_key = base58.b58decode(private_key)
            except Exception as e:
                raise ValueError(f"Error decoding private key: {str(e)}")
        
        seed = private_key[:32]
        return cls(NaclPrivateKey(seed))

    @staticmethod
    def from_file(file_path: str) -> Keypair:
        with open(file_path, 'r') as f:
            data = json.load(f)

        private_key_bytes = bytes(data[:32])
        private_key = base58.b58encode(private_key_bytes).decode('utf-8')
        keypair = Keypair.from_private_key(private_key)
        return keypair
