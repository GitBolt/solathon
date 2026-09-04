"""Small, dependency-light primitives for SPL Token and Token-2022.

The module deliberately focuses on the stable wire formats needed by clients:
associated-token addresses, checked transfers, and base mint/account state with
opaque TLV extensions. It does not pretend that extension-bearing transfers are
all interchangeable: transfer-fee, transfer-hook, non-transferable, and unknown
states are rejected unless a caller uses a specialized implementation that can
apply their semantics safely.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from enum import IntEnum

from .core.instructions import AccountMeta, Instruction
from .core.layouts import SYSTEM_PROGRAM_ID, SYSVAR_RENT_ID
from .publickey import PublicKey, PublicKeyLike

TOKEN_PROGRAM_ID = PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
TOKEN_2022_PROGRAM_ID = PublicKey("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
ASSOCIATED_TOKEN_PROGRAM_ID = PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
NATIVE_MINT = PublicKey("So11111111111111111111111111111111111111112")
TOKEN_PROGRAM_IDS = frozenset({TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID})

MINT_BASE_SIZE = 82
TOKEN_ACCOUNT_BASE_SIZE = 165
TOKEN_2022_ACCOUNT_TYPE_OFFSET = TOKEN_ACCOUNT_BASE_SIZE
TOKEN_2022_TLV_OFFSET = TOKEN_2022_ACCOUNT_TYPE_OFFSET + 1
MAX_SIGNERS = 11
U64_MAX = 2**64 - 1


class TokenAccountState(IntEnum):
    UNINITIALIZED = 0
    INITIALIZED = 1
    FROZEN = 2


class TokenAccountType(IntEnum):
    UNINITIALIZED = 0
    MINT = 1
    ACCOUNT = 2


class TokenExtensionType(IntEnum):
    """Token-2022 extension discriminants as of the current interface."""

    UNINITIALIZED = 0
    TRANSFER_FEE_CONFIG = 1
    TRANSFER_FEE_AMOUNT = 2
    MINT_CLOSE_AUTHORITY = 3
    CONFIDENTIAL_TRANSFER_MINT = 4
    CONFIDENTIAL_TRANSFER_ACCOUNT = 5
    DEFAULT_ACCOUNT_STATE = 6
    IMMUTABLE_OWNER = 7
    MEMO_TRANSFER = 8
    NON_TRANSFERABLE = 9
    INTEREST_BEARING_CONFIG = 10
    CPI_GUARD = 11
    PERMANENT_DELEGATE = 12
    NON_TRANSFERABLE_ACCOUNT = 13
    TRANSFER_HOOK = 14
    TRANSFER_HOOK_ACCOUNT = 15
    CONFIDENTIAL_TRANSFER_FEE_CONFIG = 16
    CONFIDENTIAL_TRANSFER_FEE_AMOUNT = 17
    METADATA_POINTER = 18
    TOKEN_METADATA = 19
    GROUP_POINTER = 20
    TOKEN_GROUP = 21
    GROUP_MEMBER_POINTER = 22
    TOKEN_GROUP_MEMBER = 23
    CONFIDENTIAL_MINT_BURN = 24
    SCALED_UI_AMOUNT = 25
    PAUSABLE = 26
    PAUSABLE_ACCOUNT = 27
    PERMISSIONED_BURN = 28


@dataclass(frozen=True, slots=True)
class TLVExtension:
    """One Token-2022 TLV record.

    ``type_id`` is kept as an integer so a newer on-chain extension remains
    inspectable even when this package does not know its symbolic name yet.
    """

    type_id: int
    data: bytes

    @property
    def extension_type(self) -> TokenExtensionType | None:
        try:
            return TokenExtensionType(self.type_id)
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class TokenMint:
    mint_authority: PublicKey | None
    supply: int
    decimals: int
    is_initialized: bool
    freeze_authority: PublicKey | None
    program_id: PublicKey
    extensions: tuple[TLVExtension, ...] = ()

    def has_extension(self, extension_type: TokenExtensionType | int) -> bool:
        type_id = int(extension_type)
        return any(extension.type_id == type_id for extension in self.extensions)


@dataclass(frozen=True, slots=True)
class TokenAccount:
    mint: PublicKey
    owner: PublicKey
    amount: int
    delegate: PublicKey | None
    state: TokenAccountState
    rent_exempt_reserve: int | None
    delegated_amount: int
    close_authority: PublicKey | None
    program_id: PublicKey
    extensions: tuple[TLVExtension, ...] = ()

    @property
    def is_initialized(self) -> bool:
        return self.state != TokenAccountState.UNINITIALIZED

    @property
    def is_frozen(self) -> bool:
        return self.state == TokenAccountState.FROZEN

    @property
    def is_native(self) -> bool:
        return self.rent_exempt_reserve is not None

    def has_extension(self, extension_type: TokenExtensionType | int) -> bool:
        type_id = int(extension_type)
        return any(extension.type_id == type_id for extension in self.extensions)


class UnsupportedTokenExtensionError(ValueError):
    """Raised when a generic checked transfer cannot safely handle extensions."""


_UNSUPPORTED_TRANSFER_EXTENSIONS = {
    TokenExtensionType.TRANSFER_FEE_CONFIG: (
        "transfer-fee mints require a fee-aware Token-2022 transfer builder"
    ),
    TokenExtensionType.TRANSFER_FEE_AMOUNT: (
        "transfer-fee accounts require a fee-aware Token-2022 transfer builder"
    ),
    TokenExtensionType.TRANSFER_HOOK: (
        "transfer-hook mints require resolving the hook's extra account metas"
    ),
    TokenExtensionType.TRANSFER_HOOK_ACCOUNT: (
        "transfer-hook accounts require resolving the hook's extra account metas"
    ),
    TokenExtensionType.NON_TRANSFERABLE: "non-transferable mints cannot transfer tokens",
    TokenExtensionType.NON_TRANSFERABLE_ACCOUNT: (
        "non-transferable token accounts cannot transfer tokens"
    ),
}


def get_associated_token_address(
    owner: PublicKeyLike,
    mint: PublicKeyLike,
    token_program_id: PublicKeyLike = TOKEN_PROGRAM_ID,
) -> PublicKey:
    """Derive an ATA using the selected token program as the middle seed."""

    address, _ = get_associated_token_address_and_bump(owner, mint, token_program_id)
    return address


def get_associated_token_address_and_bump(
    owner: PublicKeyLike,
    mint: PublicKeyLike,
    token_program_id: PublicKeyLike = TOKEN_PROGRAM_ID,
) -> tuple[PublicKey, int]:
    owner_key = _as_public_key(owner, "owner")
    mint_key = _as_public_key(mint, "mint")
    program_key = _token_program(token_program_id)
    return PublicKey.find_program_address(
        [bytes(owner_key), bytes(program_key), bytes(mint_key)],
        ASSOCIATED_TOKEN_PROGRAM_ID,
    )


def create_associated_token_account(
    payer: PublicKeyLike,
    owner: PublicKeyLike,
    mint: PublicKeyLike,
    *,
    token_program_id: PublicKeyLike = TOKEN_PROGRAM_ID,
    idempotent: bool = True,
) -> Instruction:
    """Build an Associated Token Account create instruction.

    Idempotent creation is the safer default for retryable client workflows.
    """

    payer_key = _as_public_key(payer, "payer")
    owner_key = _as_public_key(owner, "owner")
    mint_key = _as_public_key(mint, "mint")
    program_key = _token_program(token_program_id)
    associated_address = get_associated_token_address(owner_key, mint_key, program_key)
    keys = [
        AccountMeta(payer_key, is_signer=True, is_writable=True),
        AccountMeta(associated_address, is_signer=False, is_writable=True),
        AccountMeta(owner_key, is_signer=False, is_writable=False),
        AccountMeta(mint_key, is_signer=False, is_writable=False),
        AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(program_key, is_signer=False, is_writable=False),
    ]
    if not idempotent:
        # The original Create variant keeps the legacy Rent sysvar account;
        # CreateIdempotent uses the six-account interface.
        keys.append(AccountMeta(SYSVAR_RENT_ID, is_signer=False, is_writable=False))
    return Instruction(
        keys=keys,
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
        data=b"\x01" if idempotent else b"",
    )


def transfer_checked(
    source: PublicKeyLike,
    mint: PublicKeyLike,
    destination: PublicKeyLike,
    authority: PublicKeyLike,
    amount: int,
    decimals: int,
    *,
    token_program_id: PublicKeyLike = TOKEN_PROGRAM_ID,
    multisig_signers: Sequence[PublicKeyLike] = (),
    extensions: Iterable[
        TLVExtension | TokenExtensionType | int | TokenMint | TokenAccount
    ] = (),
) -> Instruction:
    """Build the common ``TransferChecked`` instruction (discriminant 12).

    Pass parsed mint/account states or their extensions through ``extensions``
    for a safety check. Extensions that make a generic checked transfer unsafe,
    plus unknown future extensions, are rejected explicitly.
    """

    program_key = _token_program(token_program_id)
    amount = _u64(amount, "amount")
    if not isinstance(decimals, int) or isinstance(decimals, bool):
        raise TypeError("decimals must be an integer")
    if not 0 <= decimals <= 255:
        raise ValueError("decimals must fit in an unsigned byte")
    ensure_transfer_extensions_supported(extensions)

    signer_keys = [
        _as_public_key(signer, "multisig signer") for signer in multisig_signers
    ]
    if len(signer_keys) > MAX_SIGNERS:
        raise ValueError(f"A token multisig may contain at most {MAX_SIGNERS} signers")
    if len(set(signer_keys)) != len(signer_keys):
        raise ValueError("multisig_signers cannot contain duplicates")

    authority_key = _as_public_key(authority, "authority")
    keys = [
        AccountMeta(_as_public_key(source, "source"), False, True),
        AccountMeta(_as_public_key(mint, "mint"), False, False),
        AccountMeta(_as_public_key(destination, "destination"), False, True),
        AccountMeta(authority_key, not signer_keys, False),
    ]
    keys.extend(AccountMeta(signer, True, False) for signer in signer_keys)
    return Instruction(
        keys=keys,
        program_id=program_key,
        data=bytes([12]) + amount.to_bytes(8, "little") + bytes([decimals]),
    )


create_transfer_checked_instruction = transfer_checked


def ensure_transfer_extensions_supported(
    extensions: Iterable[
        TLVExtension | TokenExtensionType | int | TokenMint | TokenAccount
    ],
) -> None:
    """Reject extensions requiring logic absent from a basic checked transfer."""

    for value in extensions:
        nested: Iterable[TLVExtension | TokenExtensionType | int]
        if isinstance(value, (TokenMint, TokenAccount)):
            nested = value.extensions
        else:
            nested = (value,)
        for extension in nested:
            type_id = (
                extension.type_id
                if isinstance(extension, TLVExtension)
                else int(extension)
            )
            try:
                extension_type = TokenExtensionType(type_id)
            except ValueError as error:
                raise UnsupportedTokenExtensionError(
                    f"unknown Token-2022 extension {type_id} may require "
                    "specialized transfer handling"
                ) from error
            reason = _UNSUPPORTED_TRANSFER_EXTENSIONS.get(extension_type)
            if reason is not None:
                raise UnsupportedTokenExtensionError(reason)


def token_amount_to_base_units(
    amount: Decimal | int | float | str,
    decimals: int,
) -> int:
    """Convert a UI token amount to its exact unsigned 64-bit base units."""

    if not isinstance(decimals, int) or isinstance(decimals, bool):
        raise TypeError("decimals must be an integer")
    if not 0 <= decimals <= 255:
        raise ValueError("decimals must fit in an unsigned byte")
    if isinstance(amount, bool):
        raise TypeError("amount must be numeric")
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError) as error:
        raise TypeError("amount must be numeric") from error
    if not value.is_finite() or value < 0:
        raise ValueError("amount must be a non-negative finite number")
    with localcontext() as context:
        context.prec = max(28, len(value.as_tuple().digits) + decimals + 1)
        base_units = value * (10**decimals)
    if base_units != base_units.to_integral_value():
        raise ValueError(f"amount cannot contain more than {decimals} decimal places")
    return _u64(int(base_units), "amount in base units")


def parse_mint(
    data: bytes | bytearray | memoryview,
    program_id: PublicKeyLike = TOKEN_PROGRAM_ID,
) -> TokenMint:
    """Parse the 82-byte mint base and any Token-2022 TLV extensions."""

    raw = bytes(data)
    program_key = _token_program(program_id)
    extensions = _state_extensions(
        raw,
        base_size=MINT_BASE_SIZE,
        account_type=TokenAccountType.MINT,
        program_id=program_key,
    )
    if len(raw) < MINT_BASE_SIZE:
        raise ValueError(f"Mint data must contain at least {MINT_BASE_SIZE} bytes")
    initialized = raw[45]
    if initialized not in (0, 1):
        raise ValueError("Mint initialization flag is invalid")
    return TokenMint(
        mint_authority=_coption_public_key(raw[0:36], "mint authority"),
        supply=int.from_bytes(raw[36:44], "little"),
        decimals=raw[44],
        is_initialized=bool(initialized),
        freeze_authority=_coption_public_key(raw[46:82], "freeze authority"),
        program_id=program_key,
        extensions=extensions,
    )


def parse_token_account(
    data: bytes | bytearray | memoryview,
    program_id: PublicKeyLike = TOKEN_PROGRAM_ID,
) -> TokenAccount:
    """Parse the 165-byte token-account base and Token-2022 TLV extensions."""

    raw = bytes(data)
    program_key = _token_program(program_id)
    extensions = _state_extensions(
        raw,
        base_size=TOKEN_ACCOUNT_BASE_SIZE,
        account_type=TokenAccountType.ACCOUNT,
        program_id=program_key,
    )
    if len(raw) < TOKEN_ACCOUNT_BASE_SIZE:
        raise ValueError(
            f"Token account data must contain at least {TOKEN_ACCOUNT_BASE_SIZE} bytes"
        )
    try:
        state = TokenAccountState(raw[108])
    except ValueError as error:
        raise ValueError("Token account state is invalid") from error
    return TokenAccount(
        mint=PublicKey(raw[0:32]),
        owner=PublicKey(raw[32:64]),
        amount=int.from_bytes(raw[64:72], "little"),
        delegate=_coption_public_key(raw[72:108], "delegate"),
        state=state,
        rent_exempt_reserve=_coption_u64(raw[109:121], "native reserve"),
        delegated_amount=int.from_bytes(raw[121:129], "little"),
        close_authority=_coption_public_key(raw[129:165], "close authority"),
        program_id=program_key,
        extensions=extensions,
    )


def parse_tlv_extensions(
    data: bytes | bytearray | memoryview,
) -> tuple[TLVExtension, ...]:
    """Parse Token-2022 TLV records, retaining records with unknown type IDs."""

    raw = bytes(data)
    extensions: list[TLVExtension] = []
    offset = 0
    while offset < len(raw):
        remaining = raw[offset:]
        if len(remaining) < 2:
            if any(remaining):
                raise ValueError("Token-2022 TLV data ends inside an extension type")
            break
        type_id = int.from_bytes(remaining[0:2], "little")
        if type_id == TokenExtensionType.UNINITIALIZED:
            if any(remaining):
                raise ValueError("Non-zero data follows the Token-2022 TLV terminator")
            break
        if len(remaining) < 4:
            raise ValueError("Token-2022 TLV data ends inside an extension header")
        length = int.from_bytes(remaining[2:4], "little")
        value_end = offset + 4 + length
        if value_end > len(raw):
            raise ValueError("Token-2022 TLV extension exceeds the account data")
        extensions.append(TLVExtension(type_id, raw[offset + 4 : value_end]))
        offset = value_end
    return tuple(extensions)


def _state_extensions(
    raw: bytes,
    *,
    base_size: int,
    account_type: TokenAccountType,
    program_id: PublicKey,
) -> tuple[TLVExtension, ...]:
    if len(raw) < base_size:
        return ()
    if program_id == TOKEN_PROGRAM_ID:
        if len(raw) != base_size:
            raise ValueError(
                "Legacy SPL Token state cannot contain Token-2022 extensions"
            )
        return ()
    if len(raw) == base_size:
        return ()
    if len(raw) < TOKEN_2022_TLV_OFFSET:
        raise ValueError("Extended Token-2022 state is missing its account type")

    padding = raw[base_size:TOKEN_2022_ACCOUNT_TYPE_OFFSET]
    if any(padding):
        raise ValueError("Token-2022 base-state padding must be zero")
    actual_type = raw[TOKEN_2022_ACCOUNT_TYPE_OFFSET]
    if actual_type != account_type:
        raise ValueError(
            f"Token-2022 account type {actual_type} does not match {account_type.name.lower()}"
        )
    return parse_tlv_extensions(raw[TOKEN_2022_TLV_OFFSET:])


def _coption_public_key(data: bytes, field: str) -> PublicKey | None:
    if len(data) != 36:
        raise ValueError(f"{field} option must contain 36 bytes")
    tag = int.from_bytes(data[:4], "little")
    if tag == 0:
        return None
    if tag == 1:
        return PublicKey(data[4:])
    raise ValueError(f"{field} option tag is invalid")


def _coption_u64(data: bytes, field: str) -> int | None:
    if len(data) != 12:
        raise ValueError(f"{field} option must contain 12 bytes")
    tag = int.from_bytes(data[:4], "little")
    if tag == 0:
        return None
    if tag == 1:
        return int.from_bytes(data[4:], "little")
    raise ValueError(f"{field} option tag is invalid")


def _as_public_key(value: PublicKeyLike, field: str) -> PublicKey:
    if isinstance(value, PublicKey):
        return value
    try:
        return PublicKey(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field} public key") from error


def _token_program(value: PublicKeyLike) -> PublicKey:
    program_id = _as_public_key(value, "token program")
    if program_id not in TOKEN_PROGRAM_IDS:
        raise ValueError("token_program_id must be SPL Token or Token-2022")
    return program_id


def _u64(value: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field} must be an integer")
    if not 0 <= value <= U64_MAX:
        raise ValueError(f"{field} must fit in an unsigned 64-bit integer")
    return value


__all__ = [
    "ASSOCIATED_TOKEN_PROGRAM_ID",
    "MINT_BASE_SIZE",
    "NATIVE_MINT",
    "TOKEN_2022_PROGRAM_ID",
    "TOKEN_ACCOUNT_BASE_SIZE",
    "TOKEN_PROGRAM_ID",
    "TOKEN_PROGRAM_IDS",
    "TLVExtension",
    "TokenAccount",
    "TokenAccountState",
    "TokenAccountType",
    "TokenExtensionType",
    "TokenMint",
    "UnsupportedTokenExtensionError",
    "create_associated_token_account",
    "create_transfer_checked_instruction",
    "ensure_transfer_extensions_supported",
    "get_associated_token_address",
    "get_associated_token_address_and_bump",
    "parse_mint",
    "parse_tlv_extensions",
    "parse_token_account",
    "token_amount_to_base_units",
    "transfer_checked",
]
