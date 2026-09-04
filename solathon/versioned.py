"""Modern Solana versioned messages and transactions.

The public objects in this module use Solathon's ``PublicKey`` and message
types at their boundary while delegating compilation, validation, signing,
and wire encoding to ``solders``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from base58 import b58decode, b58encode
from solders.address_lookup_table_account import (
    LOOKUP_TABLE_MAX_ADDRESSES,
    LOOKUP_TABLE_META_SIZE,
)
from solders.address_lookup_table_account import (
    AddressLookupTable as SoldersAddressLookupTable,
)
from solders.address_lookup_table_account import (
    AddressLookupTableAccount as SoldersAddressLookupTableAccount,
)
from solders.hash import Hash
from solders.instruction import (
    AccountMeta as SoldersAccountMeta,
)
from solders.instruction import (
    CompiledInstruction as SoldersCompiledInstruction,
)
from solders.instruction import (
    Instruction as SoldersInstruction,
)
from solders.keypair import Keypair as SoldersKeypair
from solders.message import (
    MessageAddressTableLookup as SoldersMessageAddressTableLookup,
)
from solders.message import (
    MessageHeader as SoldersMessageHeader,
)
from solders.message import (
    MessageV0 as SoldersMessageV0,
)
from solders.message import (
    MessageV1 as SoldersMessageV1,
)
from solders.message import (
    TransactionConfig as SoldersTransactionConfig,
)
from solders.message import (
    from_bytes_versioned,
    to_bytes_versioned,
)
from solders.message.v1 import (
    DEFAULT_HEAP_SIZE,
    MAX_HEAP_SIZE,
    MAX_TRANSACTION_SIZE,
    MIN_HEAP_SIZE,
)
from solders.message.v1 import (
    MAX_ADDRESSES as V1_MAX_ADDRESSES,
)
from solders.message.v1 import (
    MAX_INSTRUCTIONS as V1_MAX_INSTRUCTIONS,
)
from solders.message.v1 import (
    MAX_SIGNATURES as V1_MAX_SIGNATURES,
)
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction as SoldersVersionedTransaction

from .core.instructions import Instruction
from .core.message import CompiledInstruction, Message, MessageHeader, encode_length
from .keypair import Keypair
from .publickey import PublicKey
from .transaction import DEFAULT_SIGNATURE, PACKET_DATA_SIZE

_COMPUTE_BUDGET_PROGRAM_ID = Pubkey.from_string(
    "ComputeBudget111111111111111111111111111111"
)


def _public_key(value: PublicKey | Pubkey | str | bytes) -> PublicKey:
    return value if isinstance(value, PublicKey) else PublicKey(value)


def _message_header(value: MessageHeader | SoldersMessageHeader) -> MessageHeader:
    return MessageHeader(
        value.num_required_signatures,
        value.num_readonly_signed_accounts,
        value.num_readonly_unsigned_accounts,
    )


def _solders_header(
    value: MessageHeader | SoldersMessageHeader,
) -> SoldersMessageHeader:
    if isinstance(value, SoldersMessageHeader):
        return value
    return SoldersMessageHeader(
        value.num_required_signatures,
        value.num_readonly_signed_accounts,
        value.num_readonly_unsigned_accounts,
    )


def _compiled_instruction(
    value: CompiledInstruction | SoldersCompiledInstruction,
) -> CompiledInstruction:
    if isinstance(value, SoldersCompiledInstruction):
        return CompiledInstruction(
            accounts=bytes(value.accounts),
            program_id_index=value.program_id_index,
            data=b58encode(bytes(value.data)),
        )
    return CompiledInstruction(
        accounts=bytes(value.accounts),
        program_id_index=value.program_id_index,
        data=bytes(value.data),
    )


def _solders_compiled_instruction(
    value: CompiledInstruction | SoldersCompiledInstruction,
) -> SoldersCompiledInstruction:
    if isinstance(value, SoldersCompiledInstruction):
        return value
    return SoldersCompiledInstruction(
        value.program_id_index,
        b58decode(value.data),
        bytes(value.accounts),
    )


def _solders_instruction(value: Instruction | SoldersInstruction) -> SoldersInstruction:
    if isinstance(value, SoldersInstruction):
        return value
    if not isinstance(value, Instruction):
        raise TypeError("Instructions must be Solathon or solders Instruction objects")
    return SoldersInstruction(
        _public_key(value.program_id).to_solders(),
        bytes(value.data),
        [
            SoldersAccountMeta(
                _public_key(meta.public_key).to_solders(),
                meta.is_signer,
                meta.is_writable,
            )
            for meta in value.keys
        ],
    )


def _is_compute_budget_instruction(
    value: Instruction | SoldersInstruction,
) -> bool:
    if isinstance(value, SoldersInstruction):
        return value.program_id == _COMPUTE_BUDGET_PROGRAM_ID
    return _public_key(value.program_id).to_solders() == _COMPUTE_BUDGET_PROGRAM_ID


def _raise_solders_error(context: str, error: Exception) -> ValueError:
    detail = str(error).strip()
    return ValueError(f"{context}: {detail}" if detail else context)


@dataclass(frozen=True)
class AddressLookupTableAccount:
    """An address lookup table ready for v0 message compilation."""

    key: PublicKey
    addresses: Sequence[PublicKey]

    def __post_init__(self) -> None:
        key = _public_key(self.key)
        if isinstance(self.addresses, (str, bytes, bytearray, memoryview)):
            raise TypeError("addresses must be a sequence of public keys")
        addresses = tuple(_public_key(address) for address in self.addresses)
        if len(addresses) > LOOKUP_TABLE_MAX_ADDRESSES:
            raise ValueError(
                "An address lookup table cannot contain more than "
                f"{LOOKUP_TABLE_MAX_ADDRESSES} addresses"
            )
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "addresses", addresses)

    def to_solders(self) -> SoldersAddressLookupTableAccount:
        return SoldersAddressLookupTableAccount(
            self.key.to_solders(),
            [address.to_solders() for address in self.addresses],
        )

    @classmethod
    def from_solders(
        cls, value: SoldersAddressLookupTableAccount
    ) -> AddressLookupTableAccount:
        if not isinstance(value, SoldersAddressLookupTableAccount):
            raise TypeError("value must be a solders AddressLookupTableAccount")
        return cls(
            PublicKey.from_solders(value.key),
            [PublicKey.from_solders(address) for address in value.addresses],
        )

    @classmethod
    def from_account_data(
        cls,
        key: PublicKey | Pubkey | str | bytes,
        data: bytes | bytearray | memoryview,
    ) -> AddressLookupTableAccount:
        """Decode the data returned by ``getAccountInfo`` for a lookup table.

        Lookup-table program accounts contain a 56-byte state/metadata region
        followed by zero or more raw 32-byte public keys. ``solders`` validates
        the program-state discriminator and metadata; the checks here provide
        clearer errors for truncated or misaligned RPC data.
        """

        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("Address lookup table account data must be bytes-like")
        raw = bytes(data)
        if len(raw) < LOOKUP_TABLE_META_SIZE:
            raise ValueError(
                "Address lookup table account data is shorter than its "
                f"{LOOKUP_TABLE_META_SIZE}-byte metadata region"
            )
        addresses_size = len(raw) - LOOKUP_TABLE_META_SIZE
        if addresses_size % PublicKey.LENGTH:
            raise ValueError(
                "Address lookup table account data has a partial 32-byte address"
            )
        address_count = addresses_size // PublicKey.LENGTH
        if address_count > LOOKUP_TABLE_MAX_ADDRESSES:
            raise ValueError(
                "Address lookup table account data contains more than "
                f"{LOOKUP_TABLE_MAX_ADDRESSES} addresses"
            )
        try:
            table = SoldersAddressLookupTable.deserialize(raw)
        except Exception as error:
            raise _raise_solders_error(
                "Invalid address lookup table account data", error
            ) from error
        if len(table.addresses) != address_count:
            raise ValueError("Address lookup table account data has an invalid layout")
        return cls(
            _public_key(key),
            [PublicKey.from_solders(address) for address in table.addresses],
        )

    @classmethod
    def deserialize(
        cls,
        key: PublicKey | Pubkey | str | bytes,
        data: bytes | bytearray | memoryview,
    ) -> AddressLookupTableAccount:
        """Alias for :meth:`from_account_data`."""

        return cls.from_account_data(key, data)


@dataclass(frozen=True)
class MessageAddressTableLookup:
    account_key: PublicKey
    writable_indexes: bytes
    readonly_indexes: bytes

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_key", _public_key(self.account_key))
        if not isinstance(
            self.writable_indexes, (bytes, bytearray, memoryview)
        ) or not isinstance(self.readonly_indexes, (bytes, bytearray, memoryview)):
            raise TypeError("Lookup table indexes must be bytes-like")
        object.__setattr__(self, "writable_indexes", bytes(self.writable_indexes))
        object.__setattr__(self, "readonly_indexes", bytes(self.readonly_indexes))

    def serialize(self) -> bytes:
        return b"".join(
            [
                bytes(self.account_key),
                encode_length(len(self.writable_indexes)),
                self.writable_indexes,
                encode_length(len(self.readonly_indexes)),
                self.readonly_indexes,
            ]
        )

    def to_solders(self) -> SoldersMessageAddressTableLookup:
        return SoldersMessageAddressTableLookup(
            self.account_key.to_solders(),
            self.writable_indexes,
            self.readonly_indexes,
        )

    @classmethod
    def from_solders(
        cls, value: SoldersMessageAddressTableLookup
    ) -> MessageAddressTableLookup:
        if not isinstance(value, SoldersMessageAddressTableLookup):
            raise TypeError("value must be a solders MessageAddressTableLookup")
        return cls(
            PublicKey.from_solders(value.account_key),
            bytes(value.writable_indexes),
            bytes(value.readonly_indexes),
        )


class TransactionConfig(SoldersTransactionConfig):
    """Inline execution configuration for an experimental v1 message.

    ``priority_fee`` is the transaction's total priority fee in lamports.
    Solathon requires positive compute-unit and loaded-account-data limits when
    a v1 message is compiled or signed, rather than relying on implicit values.
    """

    def validate_for_execution(self) -> None:
        if self.compute_unit_limit is None or self.compute_unit_limit <= 0:
            raise ValueError(
                "MessageV1 requires an explicit positive compute_unit_limit"
            )
        if (
            self.loaded_accounts_data_size_limit is None
            or self.loaded_accounts_data_size_limit <= 0
        ):
            raise ValueError(
                "MessageV1 requires an explicit positive "
                "loaded_accounts_data_size_limit"
            )

    @classmethod
    def from_solders(cls, value: SoldersTransactionConfig) -> TransactionConfig:
        if not isinstance(value, SoldersTransactionConfig):
            raise TypeError("value must be a solders TransactionConfig")
        return cls(
            priority_fee=value.priority_fee,
            compute_unit_limit=value.compute_unit_limit,
            loaded_accounts_data_size_limit=value.loaded_accounts_data_size_limit,
            heap_size=value.heap_size,
        )

    def to_solders(self) -> SoldersTransactionConfig:
        return SoldersTransactionConfig(
            priority_fee=self.priority_fee,
            compute_unit_limit=self.compute_unit_limit,
            loaded_accounts_data_size_limit=self.loaded_accounts_data_size_limit,
            heap_size=self.heap_size,
        )


class MessageV0(Message):
    """A v0 message with address lookup table support."""

    VERSION = 0
    VERSION_PREFIX = bytes([0x80])

    def __init__(
        self,
        header: MessageHeader | SoldersMessageHeader,
        account_keys: Sequence[PublicKey | Pubkey | str | bytes],
        instructions: Sequence[CompiledInstruction | SoldersCompiledInstruction],
        recent_blockhash: str | Hash,
        address_table_lookups: Sequence[
            MessageAddressTableLookup | SoldersMessageAddressTableLookup
        ],
    ) -> None:
        normalized_instructions = [
            _compiled_instruction(instruction) for instruction in instructions
        ]
        super().__init__(
            _message_header(header),
            [_public_key(key) for key in account_keys],
            normalized_instructions,
            str(recent_blockhash),
        )
        self.address_table_lookups = [
            lookup
            if isinstance(lookup, MessageAddressTableLookup)
            else MessageAddressTableLookup.from_solders(lookup)
            for lookup in address_table_lookups
        ]

    @property
    def static_account_keys(self) -> list[PublicKey]:
        return self.account_keys

    @property
    def _loaded_writable_count(self) -> int:
        return sum(
            len(lookup.writable_indexes) for lookup in self.address_table_lookups
        )

    @property
    def _loaded_readonly_count(self) -> int:
        return sum(
            len(lookup.readonly_indexes) for lookup in self.address_table_lookups
        )

    def is_account_signer(self, index: int) -> bool:
        total = (
            len(self.account_keys)
            + self._loaded_writable_count
            + self._loaded_readonly_count
        )
        if not 0 <= index < total:
            raise IndexError("Account index is outside the message")
        if index >= len(self.account_keys):
            return False
        return super().is_account_signer(index)

    def is_account_writable(self, index: int) -> bool:
        static_count = len(self.account_keys)
        total = static_count + self._loaded_writable_count + self._loaded_readonly_count
        if not 0 <= index < total:
            raise IndexError("Account index is outside the message")
        if index < static_count:
            return super().is_account_writable(index)
        return index < static_count + self._loaded_writable_count

    @classmethod
    def compile(
        cls,
        payer: PublicKey | Pubkey | str | bytes,
        instructions: Iterable[Instruction | SoldersInstruction],
        recent_blockhash: str | Hash,
        lookup_tables: Iterable[
            AddressLookupTableAccount | SoldersAddressLookupTableAccount
        ] = (),
    ) -> MessageV0:
        native_instructions = [
            _solders_instruction(instruction) for instruction in instructions
        ]
        native_tables = [
            table.to_solders()
            if isinstance(table, AddressLookupTableAccount)
            else table
            for table in lookup_tables
        ]
        if not all(
            isinstance(table, SoldersAddressLookupTableAccount)
            for table in native_tables
        ):
            raise TypeError(
                "lookup_tables must contain Solathon or solders "
                "AddressLookupTableAccount objects"
            )
        try:
            message = SoldersMessageV0.try_compile(
                _public_key(payer).to_solders(),
                native_instructions,
                native_tables,
                Hash.from_string(str(recent_blockhash)),
            )
            message.sanitize()
        except Exception as error:
            raise _raise_solders_error("Could not compile MessageV0", error) from error
        return cls.from_solders(message)

    def to_solders(self) -> SoldersMessageV0:  # type: ignore[override]
        try:
            message = SoldersMessageV0(
                _solders_header(self.header),
                [key.to_solders() for key in self.account_keys],
                Hash.from_string(self.recent_blockhash),
                [
                    _solders_compiled_instruction(instruction)
                    for instruction in self.instructions
                ],
                [lookup.to_solders() for lookup in self.address_table_lookups],
            )
            message.sanitize()
            return message
        except Exception as error:
            raise _raise_solders_error("Invalid MessageV0", error) from error

    @classmethod
    def from_solders(  # type: ignore[override]
        cls, message: SoldersMessageV0
    ) -> MessageV0:
        if not isinstance(message, SoldersMessageV0):
            raise TypeError("message must be a solders MessageV0")
        try:
            message.sanitize()
        except Exception as error:
            raise _raise_solders_error("Invalid MessageV0", error) from error
        return cls(
            message.header,
            list(message.account_keys),
            list(message.instructions),
            message.recent_blockhash,
            [
                MessageAddressTableLookup.from_solders(lookup)
                for lookup in message.address_table_lookups
            ],
        )

    def serialize(self) -> bytes:
        return to_bytes_versioned(self.to_solders())

    @classmethod
    def from_buffer(cls, buffer: bytes | bytearray | memoryview) -> MessageV0:
        if not isinstance(buffer, (bytes, bytearray, memoryview)):
            raise TypeError("Versioned message buffer must be bytes-like")
        try:
            message = from_bytes_versioned(bytes(buffer))
        except Exception as error:
            raise _raise_solders_error("Invalid versioned message", error) from error
        if not isinstance(message, SoldersMessageV0):
            raise ValueError("Buffer does not contain a v0 message")
        return cls.from_solders(message)


class MessageV1(Message):
    """Experimental SIMD-0385 v1 message with inline execution limits.

    V1 messages do not support address lookup tables. Compute Budget program
    instructions are also rejected because v1 carries those settings inline
    and would otherwise silently ignore the instructions.
    """

    VERSION = 1
    VERSION_PREFIX = bytes([0x81])
    MAX_TRANSACTION_SIZE = MAX_TRANSACTION_SIZE
    MAX_ADDRESSES = V1_MAX_ADDRESSES
    MAX_INSTRUCTIONS = V1_MAX_INSTRUCTIONS
    MAX_SIGNATURES = V1_MAX_SIGNATURES
    MIN_HEAP_SIZE = MIN_HEAP_SIZE
    MAX_HEAP_SIZE = MAX_HEAP_SIZE
    DEFAULT_HEAP_SIZE = DEFAULT_HEAP_SIZE

    def __init__(
        self,
        header: MessageHeader | SoldersMessageHeader,
        account_keys: Sequence[PublicKey | Pubkey | str | bytes],
        instructions: Sequence[CompiledInstruction | SoldersCompiledInstruction],
        recent_blockhash: str | Hash,
        config: TransactionConfig | SoldersTransactionConfig,
        address_table_lookups: Sequence[object] = (),
    ) -> None:
        if address_table_lookups:
            raise ValueError("MessageV1 does not support address lookup tables")
        normalized_config = (
            config
            if isinstance(config, TransactionConfig)
            else TransactionConfig.from_solders(config)
        )
        normalized_instructions = [
            _compiled_instruction(instruction) for instruction in instructions
        ]
        super().__init__(
            _message_header(header),
            [_public_key(key) for key in account_keys],
            normalized_instructions,
            str(recent_blockhash),
        )
        self.config = normalized_config

    @property
    def static_account_keys(self) -> list[PublicKey]:
        return self.account_keys

    @property
    def lifetime_specifier(self) -> str:
        return self.recent_blockhash

    @property
    def address_table_lookups(self) -> tuple[MessageAddressTableLookup, ...]:
        return ()

    @classmethod
    def compile(
        cls,
        payer: PublicKey | Pubkey | str | bytes,
        instructions: Iterable[Instruction | SoldersInstruction],
        recent_blockhash: str | Hash,
        config: TransactionConfig | SoldersTransactionConfig,
        lookup_tables: Iterable[object] = (),
    ) -> MessageV1:
        if list(lookup_tables):
            raise ValueError("MessageV1 does not support address lookup tables")
        normalized_config = (
            config
            if isinstance(config, TransactionConfig)
            else TransactionConfig.from_solders(config)
        )
        normalized_config.validate_for_execution()
        instruction_list = list(instructions)
        if any(_is_compute_budget_instruction(item) for item in instruction_list):
            raise ValueError(
                "Compute Budget program instructions are no-ops in MessageV1; "
                "set their values on TransactionConfig instead"
            )
        try:
            message = SoldersMessageV1.try_compile(
                _public_key(payer).to_solders(),
                [_solders_instruction(item) for item in instruction_list],
                Hash.from_string(str(recent_blockhash)),
                normalized_config.to_solders(),
            )
            message.validate()
        except Exception as error:
            raise _raise_solders_error("Could not compile MessageV1", error) from error
        return cls.from_solders(message)

    def _validate_execution_invariants(self) -> None:
        self.config.validate_for_execution()
        try:
            message = self.to_solders()
        except ValueError:
            raise
        for instruction in message.instructions:
            program_index = instruction.program_id_index
            if (
                program_index < len(message.account_keys)
                and message.account_keys[program_index] == _COMPUTE_BUDGET_PROGRAM_ID
            ):
                raise ValueError(
                    "Compute Budget program instructions are no-ops in MessageV1; "
                    "set their values on TransactionConfig instead"
                )

    def to_solders(self) -> SoldersMessageV1:  # type: ignore[override]
        try:
            message = SoldersMessageV1(
                _solders_header(self.header),
                self.config.to_solders(),
                Hash.from_string(self.recent_blockhash),
                [key.to_solders() for key in self.account_keys],
                [
                    _solders_compiled_instruction(instruction)
                    for instruction in self.instructions
                ],
            )
            message.sanitize()
            message.validate()
            return message
        except Exception as error:
            raise _raise_solders_error("Invalid MessageV1", error) from error

    @classmethod
    def from_solders(  # type: ignore[override]
        cls, message: SoldersMessageV1
    ) -> MessageV1:
        if not isinstance(message, SoldersMessageV1):
            raise TypeError("message must be a solders MessageV1")
        try:
            message.sanitize()
            message.validate()
        except Exception as error:
            raise _raise_solders_error("Invalid MessageV1", error) from error
        return cls(
            message.header,
            list(message.account_keys),
            list(message.instructions),
            message.lifetime_specifier,
            TransactionConfig.from_solders(message.config),
        )

    def serialize(self) -> bytes:
        return to_bytes_versioned(self.to_solders())

    @classmethod
    def from_buffer(cls, buffer: bytes | bytearray | memoryview) -> MessageV1:
        if not isinstance(buffer, (bytes, bytearray, memoryview)):
            raise TypeError("Versioned message buffer must be bytes-like")
        try:
            message = from_bytes_versioned(bytes(buffer))
        except Exception as error:
            raise _raise_solders_error("Invalid versioned message", error) from error
        if not isinstance(message, SoldersMessageV1):
            raise ValueError("Buffer does not contain a v1 message")
        return cls.from_solders(message)


VersionedMessage = MessageV0 | MessageV1


class VersionedTransaction:
    """A signed v0 or experimental v1 transaction."""

    def __init__(
        self,
        message: VersionedMessage | SoldersMessageV0 | SoldersMessageV1,
        signers: Iterable[Keypair | SoldersKeypair] = (),
    ) -> None:
        if isinstance(message, SoldersMessageV0):
            message = MessageV0.from_solders(message)
        elif isinstance(message, SoldersMessageV1):
            message = MessageV1.from_solders(message)
        elif not isinstance(message, (MessageV0, MessageV1)):
            raise TypeError("message must be a v0 or v1 message")
        self.message = message
        self.signers = list(signers)
        if not all(
            isinstance(signer, (Keypair, SoldersKeypair)) for signer in self.signers
        ):
            raise TypeError("signers must contain Solathon or solders Keypair objects")
        self.signatures = [
            DEFAULT_SIGNATURE for _ in range(message.header.num_required_signatures)
        ]

    @property
    def recent_blockhash(self) -> str:
        return self.message.recent_blockhash

    @property
    def version(self) -> int:
        return self.message.VERSION

    def _message_data(self) -> bytes:
        if isinstance(self.message, MessageV1):
            self.message._validate_execution_invariants()
        return self.message.serialize()

    def _required_signer_keys(self) -> list[PublicKey]:
        count = self.message.header.num_required_signatures
        return self.message.static_account_keys[:count]

    @staticmethod
    def _solders_keypair(value: Keypair | SoldersKeypair) -> SoldersKeypair:
        return value.to_solders() if isinstance(value, Keypair) else value

    def sign(self) -> None:
        message_data = self._message_data()
        signer_indices = {
            public_key: index
            for index, public_key in enumerate(self._required_signer_keys())
        }
        for signer in self.signers:
            native_signer = self._solders_keypair(signer)
            public_key = PublicKey.from_solders(native_signer.pubkey())
            index = signer_indices.get(public_key)
            if index is None:
                raise ValueError("Signer is not required by the versioned message")
            self.signatures[index] = bytes(native_signer.sign_message(message_data))

    def add_signature(
        self,
        public_key: PublicKey | Pubkey | str | bytes,
        signature: bytes | bytearray | memoryview | Signature,
    ) -> None:
        normalized_key = _public_key(public_key)
        raw_signature = bytes(signature)
        if len(raw_signature) != Signature.LENGTH:
            raise ValueError(f"Signature must contain {Signature.LENGTH} bytes")
        try:
            index = self._required_signer_keys().index(normalized_key)
        except ValueError as error:
            raise ValueError("Public key is not a required message signer") from error
        native_signature = Signature.from_bytes(raw_signature)
        if not native_signature.verify(
            normalized_key.to_solders(), self._message_data()
        ):
            raise ValueError("Signature does not match the versioned message")
        self.signatures[index] = raw_signature

    def verify_signatures(self) -> bool:
        if len(self.signatures) != len(self._required_signer_keys()):
            return False
        try:
            message_data = self._message_data()
        except ValueError:
            return False
        for public_key, signature in zip(
            self._required_signer_keys(), self.signatures, strict=True
        ):
            if signature == DEFAULT_SIGNATURE:
                return False
            try:
                valid = Signature.from_bytes(signature).verify(
                    public_key.to_solders(), message_data
                )
            except (TypeError, ValueError):
                return False
            if not valid:
                return False
        return True

    def verify_present_signatures(self) -> bool:
        if len(self.signatures) != len(self._required_signer_keys()):
            return False
        try:
            message_data = self._message_data()
        except ValueError:
            return False
        for public_key, signature in zip(
            self._required_signer_keys(), self.signatures, strict=True
        ):
            if signature == DEFAULT_SIGNATURE:
                continue
            try:
                valid = Signature.from_bytes(signature).verify(
                    public_key.to_solders(), message_data
                )
            except (TypeError, ValueError):
                return False
            if not valid:
                return False
        return True

    def to_solders(self) -> SoldersVersionedTransaction:
        if len(self.signatures) != self.message.header.num_required_signatures:
            raise ValueError("Signature count does not match the versioned message")
        try:
            return SoldersVersionedTransaction.populate(
                self.message.to_solders(),
                [Signature.from_bytes(signature) for signature in self.signatures],
            )
        except Exception as error:
            raise _raise_solders_error(
                "Invalid versioned transaction", error
            ) from error

    @classmethod
    def from_solders(
        cls, transaction: SoldersVersionedTransaction
    ) -> VersionedTransaction:
        if not isinstance(transaction, SoldersVersionedTransaction):
            raise TypeError("transaction must be a solders VersionedTransaction")
        try:
            transaction.sanitize()
        except Exception as error:
            raise _raise_solders_error(
                "Invalid versioned transaction", error
            ) from error
        if isinstance(transaction.message, SoldersMessageV0):
            message: VersionedMessage = MessageV0.from_solders(transaction.message)
        elif isinstance(transaction.message, SoldersMessageV1):
            message = MessageV1.from_solders(transaction.message)
        else:
            raise ValueError("Legacy transactions are not versioned transactions")
        result = cls(message)
        result.signatures = [bytes(signature) for signature in transaction.signatures]
        if len(result.signatures) != message.header.num_required_signatures:
            raise ValueError("Signature count does not match the versioned message")
        return result

    @classmethod
    def _from_solders_unchecked(
        cls, transaction: SoldersVersionedTransaction
    ) -> VersionedTransaction:
        """Decode the temporary unsanitized template allowed by Solana Pay."""

        native_message = transaction.message
        if isinstance(native_message, SoldersMessageV0):
            message: VersionedMessage = MessageV0(
                native_message.header,
                list(native_message.account_keys),
                list(native_message.instructions),
                native_message.recent_blockhash,
                list(native_message.address_table_lookups),
            )
        elif isinstance(native_message, SoldersMessageV1):
            message = MessageV1(
                native_message.header,
                list(native_message.account_keys),
                list(native_message.instructions),
                native_message.lifetime_specifier,
                TransactionConfig.from_solders(native_message.config),
            )
        else:
            raise ValueError("Legacy transactions are not versioned transactions")
        result = cls(message)
        result.signatures = [bytes(signature) for signature in transaction.signatures]
        if len(result.signatures) != message.header.num_required_signatures:
            raise ValueError("Signature count does not match the versioned message")
        return result

    def serialize(self, require_all_signatures: bool = True) -> bytes:
        if require_all_signatures:
            if not self.verify_signatures():
                raise ValueError(
                    "Versioned transaction signatures are invalid or incomplete"
                )
        elif not self.verify_present_signatures():
            raise ValueError("A present versioned transaction signature is invalid")
        wire_transaction = bytes(self.to_solders())
        limit = (
            MAX_TRANSACTION_SIZE
            if isinstance(self.message, MessageV1)
            else PACKET_DATA_SIZE
        )
        if len(wire_transaction) > limit:
            raise ValueError(
                f"Version {self.version} transaction exceeds the {limit}-byte limit"
            )
        return wire_transaction

    @classmethod
    def populate(
        cls,
        message: VersionedMessage | SoldersMessageV0 | SoldersMessageV1,
        signatures: Sequence[bytes | bytearray | memoryview | Signature],
    ) -> VersionedTransaction:
        transaction = cls(message)
        transaction.signatures = [bytes(signature) for signature in signatures]
        if len(transaction.signatures) != message.header.num_required_signatures:
            raise ValueError("Signature count does not match the versioned message")
        if any(
            len(signature) != Signature.LENGTH for signature in transaction.signatures
        ):
            raise ValueError(f"Each signature must contain {Signature.LENGTH} bytes")
        return transaction

    @classmethod
    def from_buffer(
        cls, buffer: bytes | bytearray | memoryview
    ) -> VersionedTransaction:
        return cls._from_buffer(buffer, sanitize=True)

    @classmethod
    def _from_buffer(
        cls,
        buffer: bytes | bytearray | memoryview,
        *,
        sanitize: bool,
    ) -> VersionedTransaction:
        if not isinstance(buffer, (bytes, bytearray, memoryview)):
            raise TypeError("Versioned transaction buffer must be bytes-like")
        raw = bytes(buffer)
        if not raw:
            raise ValueError("Versioned transaction buffer is empty")
        try:
            native_transaction = SoldersVersionedTransaction.from_bytes(raw)
        except Exception as error:
            raise _raise_solders_error(
                "Invalid versioned transaction buffer", error
            ) from error
        transaction = (
            cls.from_solders(native_transaction)
            if sanitize
            else cls._from_solders_unchecked(native_transaction)
        )
        limit = (
            MAX_TRANSACTION_SIZE
            if isinstance(transaction.message, MessageV1)
            else PACKET_DATA_SIZE
        )
        if len(raw) > limit:
            raise ValueError(
                f"Version {transaction.version} transaction exceeds the "
                f"{limit}-byte limit"
            )
        return transaction


__all__ = [
    "AddressLookupTableAccount",
    "MessageAddressTableLookup",
    "MessageV0",
    "MessageV1",
    "TransactionConfig",
    "VersionedTransaction",
]
