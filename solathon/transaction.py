from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from base58 import b58decode, b58encode
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from solders.signature import Signature as SoldersSignature
from solders.transaction import Transaction as SoldersTransaction

from .core.compile import ordered_account_metas
from .core.instructions import AccountMeta, Instruction
from .core.layouts import (
    SYSTEM_PROGRAM_ID,
    SYSVAR_RECENT_BLOCKHASHES_ID,
    InstructionType,
)
from .core.message import (
    CompiledInstruction,
    Message,
    MessageHeader,
)
from .keypair import Keypair
from .publickey import PublicKey

PACKET_DATA_SIZE = 1232
DEFAULT_SIGNATURE = bytes(64)


@dataclass
class PKSigPair:
    public_key: PublicKey
    signature: bytes | None = None


@dataclass(frozen=True, slots=True)
class NonceInformation:
    """Durable-nonce blockhash and mandatory advance instruction."""

    nonce: str
    nonce_instruction: Instruction

    def __post_init__(self) -> None:
        if not isinstance(self.nonce, str):
            raise TypeError("nonce must be a base58 string")
        try:
            raw_nonce = b58decode(self.nonce)
        except ValueError as error:
            raise ValueError("nonce must be valid base58") from error
        if len(raw_nonce) != PublicKey.LENGTH:
            raise ValueError("nonce must decode to 32 bytes")
        if not isinstance(self.nonce_instruction, Instruction):
            raise TypeError("nonce_instruction must be an Instruction")
        instruction = self.nonce_instruction
        expected_data = int(InstructionType.ADVANCE_NONCE_ACCOUNT).to_bytes(4, "little")
        if (
            instruction.program_id != SYSTEM_PROGRAM_ID
            or instruction.data != expected_data
            or len(instruction.keys) != 3
        ):
            raise ValueError(
                "nonce_instruction must be a canonical System "
                "AdvanceNonceAccount instruction"
            )
        nonce_account, recent_blockhashes, authority = instruction.keys
        if (
            nonce_account.is_signer
            or not nonce_account.is_writable
            or recent_blockhashes.public_key != SYSVAR_RECENT_BLOCKHASHES_ID
            or recent_blockhashes.is_signer
            or recent_blockhashes.is_writable
            or not authority.is_signer
            or authority.is_writable
        ):
            raise ValueError(
                "nonce_instruction must use canonical AdvanceNonceAccount accounts"
            )


def _nonce_information(value: object | None) -> NonceInformation | None:
    if value is None or isinstance(value, NonceInformation):
        return value
    try:
        if isinstance(value, Mapping):
            nonce = value["nonce"]
            instruction = value["nonce_instruction"]
        else:
            legacy_value: Any = value
            nonce = legacy_value.nonce
            instruction = legacy_value.nonce_instruction
    except (AttributeError, KeyError, TypeError) as error:
        raise TypeError(
            "nonce_info must be NonceInformation or expose nonce and nonce_instruction"
        ) from error
    return NonceInformation(nonce, instruction)


def _public_key(signer: PublicKey | Keypair) -> PublicKey:
    if isinstance(signer, Keypair):
        return signer.public_key
    if isinstance(signer, PublicKey):
        return signer
    raise TypeError("Signers must be PublicKey or Keypair objects")


def _meta_public_key(meta: AccountMeta) -> PublicKey:
    value = meta.public_key
    return PublicKey(bytes(value)) if isinstance(value, PublicKey) else PublicKey(value)


class Transaction:
    """A legacy Solana transaction.

    Use :class:`MessageV0` and :class:`VersionedTransaction` for address
    lookup tables and other versioned-transaction workflows.
    """

    def __init__(
        self,
        *,
        fee_payer: PublicKey | str | None = None,
        nonce_info: NonceInformation | None = None,
        recent_blockhash: str | None = None,
        signers: Iterable[PublicKey | Keypair] | None = None,
        instructions: Iterable[Instruction] | None = None,
        signatures: Iterable[PKSigPair] | None = None,
    ) -> None:
        self.fee_payer = (
            PublicKey(fee_payer) if isinstance(fee_payer, str) else fee_payer
        )
        self.nonce_info = _nonce_information(nonce_info)
        self.recent_blockhash = recent_blockhash
        self.signers = list(signers or [])
        self.instructions: list[Instruction] = []

        instruction_values = list(instructions or [])
        if not all(
            isinstance(instruction, Instruction) for instruction in instruction_values
        ):
            raise TypeError("instructions must contain only Instruction objects")
        self.instructions.extend(instruction_values)

        signature_values = list(signatures or [])
        if not all(isinstance(signature, PKSigPair) for signature in signature_values):
            raise TypeError("signatures must contain only PKSigPair objects")
        self.signatures = signature_values
        if not self.signatures:
            self.signatures = [
                PKSigPair(public_key=_public_key(signer)) for signer in self.signers
            ]
        self._message: Message | None = None
        self._message_cache_state: tuple[Any, ...] | None = None

    def _effective_instructions(self) -> list[Instruction]:
        if self.nonce_info is None:
            return self.instructions
        nonce_instruction = self.nonce_info.nonce_instruction
        if self.instructions and self.instructions[0] == nonce_instruction:
            return self.instructions
        return [nonce_instruction, *self.instructions]

    def _current_message_state(self) -> tuple[Any, ...]:
        instruction_state = tuple(
            (
                bytes(instruction.program_id),
                bytes(instruction.data),
                tuple(
                    (
                        bytes(_meta_public_key(meta)),
                        meta.is_signer,
                        meta.is_writable,
                    )
                    for meta in instruction.keys
                ),
            )
            for instruction in self._effective_instructions()
        )
        return (
            bytes(self.fee_payer) if self.fee_payer is not None else None,
            self.recent_blockhash,
            instruction_state,
            tuple(bytes(pair.public_key) for pair in self.signatures),
        )

    def _message_and_signatures(self) -> Message:
        if self.nonce_info:
            self.recent_blockhash = self.nonce_info.nonce

        instructions = self._effective_instructions()
        current_state = self._current_message_state()
        if self._message is not None and current_state == self._message_cache_state:
            return self._message

        if not instructions:
            raise ValueError("Transaction has no instructions")
        if not self.recent_blockhash:
            raise ValueError("Transaction has no recent blockhash")

        if self.fee_payer is None:
            if not self.signatures:
                raise ValueError("Transaction has no fee payer or signer")
            self.fee_payer = self.signatures[0].public_key

        signer_public_keys = [pair.public_key for pair in self.signatures]
        metas = ordered_account_metas(
            self.fee_payer,
            instructions,
            signer_public_keys,
        )
        signed_metas = [meta for meta in metas if meta.is_signer]
        unsigned_metas = [meta for meta in metas if not meta.is_signer]
        ordered_metas = [*signed_metas, *unsigned_metas]

        signature_by_key = {pair.public_key: pair.signature for pair in self.signatures}
        self.signatures = [
            PKSigPair(
                public_key=_meta_public_key(meta),
                signature=signature_by_key.get(_meta_public_key(meta)),
            )
            for meta in signed_metas
        ]

        account_keys = [_meta_public_key(meta) for meta in ordered_metas]
        account_indices = {
            public_key: index for index, public_key in enumerate(account_keys)
        }
        compiled_instructions = [
            CompiledInstruction(
                accounts=[
                    account_indices[_meta_public_key(meta)] for meta in instruction.keys
                ],
                program_id_index=account_indices[instruction.program_id],
                data=b58encode(instruction.data),
            )
            for instruction in instructions
        ]
        message = Message(
            header=MessageHeader(
                num_required_signatures=len(signed_metas),
                num_readonly_signed_accounts=sum(
                    not meta.is_writable for meta in signed_metas
                ),
                num_readonly_unsigned_accounts=sum(
                    not meta.is_writable for meta in unsigned_metas
                ),
            ),
            account_keys=account_keys,
            instructions=compiled_instructions,
            recent_blockhash=self.recent_blockhash,
        )
        self._message = message
        self._message_cache_state = self._current_message_state()
        return message

    def compile_transaction(self) -> bytes:
        return self._message_and_signatures().serialize()

    def serialize_message(self) -> bytes:
        return self.compile_transaction()

    def sign(self, signatures: list[bytes] | None = None) -> None:
        sign_data = self.compile_transaction()
        keypairs = [signer for signer in self.signers if isinstance(signer, Keypair)]

        if signatures is not None:
            if len(signatures) != len(self.signers):
                raise ValueError(
                    "Number of signatures does not match number of signers"
                )
            for signer, signature in zip(self.signers, signatures, strict=True):
                self.add_signature(_public_key(signer), signature, sign_data)
            return

        for signer in keypairs:
            self.add_signature(
                signer.public_key,
                signer.sign(sign_data).signature,
                sign_data,
            )

    def add_signature(
        self,
        public_key: PublicKey,
        signature: bytes,
        signed_data: bytes | None = None,
    ) -> None:
        if len(signature) != 64:
            raise ValueError("Signature must contain 64 bytes")
        if signed_data is None:
            signed_data = self.compile_transaction()
        try:
            VerifyKey(bytes(public_key)).verify(signed_data, signature)
        except BadSignatureError as error:
            raise ValueError(
                "Signature does not match the transaction message"
            ) from error

        for pair in self.signatures:
            if pair.public_key == public_key:
                pair.signature = signature
                return
        raise ValueError("Public key is not a required transaction signer")

    def verify_signatures(self, signed_data: bytes | None = None) -> bool:
        if signed_data is None:
            signed_data = self.compile_transaction()
        for pair in self.signatures:
            if pair.signature is None:
                return False
            try:
                VerifyKey(bytes(pair.public_key)).verify(signed_data, pair.signature)
            except (BadSignatureError, TypeError, ValueError):
                return False
        return True

    def verify_present_signatures(self, signed_data: bytes | None = None) -> bool:
        if signed_data is None:
            signed_data = self.compile_transaction()
        for pair in self.signatures:
            if pair.signature is None:
                continue
            try:
                VerifyKey(bytes(pair.public_key)).verify(signed_data, pair.signature)
            except (BadSignatureError, TypeError, ValueError):
                return False
        return True

    def serialize(
        self,
        require_all_signatures: bool = True,
        verify_signatures: bool = True,
    ) -> bytes:
        message = self._message_and_signatures()
        sign_data = message.serialize()
        if require_all_signatures and any(
            pair.signature is None for pair in self.signatures
        ):
            raise ValueError("Transaction is missing one or more signatures")
        if verify_signatures:
            signatures_are_valid = (
                self.verify_signatures(sign_data)
                if require_all_signatures
                else self.verify_present_signatures(sign_data)
            )
            if not signatures_are_valid:
                raise ValueError("Transaction signatures are invalid or incomplete")

        wire_transaction = bytes(self._to_solders(message))

        if len(wire_transaction) > PACKET_DATA_SIZE:
            raise ValueError(
                f"Transaction exceeds the {PACKET_DATA_SIZE}-byte packet limit"
            )
        return wire_transaction

    def to_solders(self) -> SoldersTransaction:
        """Return a native transaction for fast, canonical serialization."""

        return self._to_solders(self._message_and_signatures())

    def _to_solders(self, message: Message) -> SoldersTransaction:
        signatures = [
            SoldersSignature.from_bytes(pair.signature or DEFAULT_SIGNATURE)
            for pair in self.signatures
        ]
        transaction = SoldersTransaction.populate(message.to_solders(), signatures)
        transaction.sanitize()
        return transaction

    def add_instructions(self, *instructions: Instruction) -> Transaction:
        if not all(
            isinstance(instruction, Instruction) for instruction in instructions
        ):
            raise TypeError("Arguments must be Instruction objects")
        self.instructions.extend(instructions)
        return self

    @classmethod
    def populate(
        cls,
        message: Message,
        signatures: Iterable[bytes | str],
        signers: list[Keypair] | None = None,
    ) -> Transaction:
        if type(message) is not Message:
            raise TypeError("message must be a legacy Message")
        signature_values = list(signatures)
        required = message.header.num_required_signatures
        if len(signature_values) != required:
            raise ValueError(
                f"Expected {required} transaction signatures, "
                f"received {len(signature_values)}"
            )
        decoded_signatures = []
        for index in range(required):
            value = signature_values[index]
            signature = b58decode(value) if isinstance(value, str) else bytes(value)
            if len(signature) != 64:
                raise ValueError("Each transaction signature must contain 64 bytes")
            decoded_signatures.append(
                PKSigPair(
                    public_key=message.account_keys[index],
                    signature=None if signature == DEFAULT_SIGNATURE else signature,
                )
            )

        instructions = []
        for compiled in message.instructions:
            keys = [
                AccountMeta(
                    public_key=message.account_keys[index],
                    is_signer=message.is_account_signer(index),
                    is_writable=message.is_account_writable(index),
                )
                for index in compiled.accounts
            ]
            instructions.append(
                Instruction(
                    keys=keys,
                    program_id=message.account_keys[compiled.program_id_index],
                    data=b58decode(compiled.data),
                )
            )

        transaction = cls(
            fee_payer=(
                message.account_keys[0]
                if message.header.num_required_signatures
                else None
            ),
            recent_blockhash=message.recent_blockhash,
            signatures=decoded_signatures,
            instructions=instructions,
            signers=signers or [],
        )
        # Preserve the exact compiled message while the reconstructed public
        # transaction state remains unchanged. Valid messages may contain
        # unused static accounts that cannot be inferred from instructions.
        transaction._message = message
        transaction._message_cache_state = transaction._current_message_state()
        return transaction

    @classmethod
    def from_buffer(
        cls,
        buffer: bytes,
        signers: list[Keypair] | None = None,
    ) -> Transaction:
        if not isinstance(buffer, bytes):
            raise TypeError("Buffer must be a bytes object")

        if not buffer:
            raise ValueError("Transaction buffer is empty")
        if len(buffer) > PACKET_DATA_SIZE:
            raise ValueError(
                f"Transaction exceeds the {PACKET_DATA_SIZE}-byte packet limit"
            )
        transaction = SoldersTransaction.from_bytes(buffer)
        transaction.sanitize()
        return cls.populate(
            Message.from_solders(transaction.message),
            [bytes(signature) for signature in transaction.signatures],
            signers,
        )
