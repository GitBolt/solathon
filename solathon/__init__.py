from importlib import import_module
from typing import TYPE_CHECKING, Any

__version__ = "2.0.0"

if TYPE_CHECKING:
    from .async_client import AsyncClient
    from .client import Client
    from .keypair import Keypair, PrivateKey
    from .publickey import PublicKey
    from .solana_pay import (
        create_qr,
        create_transfer,
        encode_url,
        fetch_transaction,
        find_reference,
        parse_url,
        validate_transfer,
    )
    from .token import (
        ASSOCIATED_TOKEN_PROGRAM_ID,
        TOKEN_2022_PROGRAM_ID,
        TOKEN_PROGRAM_ID,
        TokenAccount,
        TokenExtensionType,
        TokenMint,
        UnsupportedTokenExtensionError,
        create_associated_token_account,
        get_associated_token_address,
        parse_mint,
        parse_token_account,
        token_amount_to_base_units,
        transfer_checked,
    )
    from .transaction import NonceInformation, Transaction
    from .versioned import (
        AddressLookupTableAccount,
        MessageAddressTableLookup,
        MessageV0,
        MessageV1,
        TransactionConfig,
        VersionedTransaction,
    )

_LAZY_EXPORTS = {
    "ASSOCIATED_TOKEN_PROGRAM_ID": ".token",
    "AddressLookupTableAccount": ".versioned",
    "AsyncClient": ".async_client",
    "Client": ".client",
    "Keypair": ".keypair",
    "MessageAddressTableLookup": ".versioned",
    "MessageV0": ".versioned",
    "MessageV1": ".versioned",
    "NonceInformation": ".transaction",
    "PrivateKey": ".keypair",
    "PublicKey": ".publickey",
    "Transaction": ".transaction",
    "TransactionConfig": ".versioned",
    "TOKEN_2022_PROGRAM_ID": ".token",
    "TOKEN_PROGRAM_ID": ".token",
    "TokenAccount": ".token",
    "TokenExtensionType": ".token",
    "TokenMint": ".token",
    "UnsupportedTokenExtensionError": ".token",
    "VersionedTransaction": ".versioned",
    "create_qr": ".solana_pay",
    "create_associated_token_account": ".token",
    "create_transfer": ".solana_pay",
    "encode_url": ".solana_pay",
    "fetch_transaction": ".solana_pay",
    "find_reference": ".solana_pay",
    "get_associated_token_address": ".token",
    "parse_mint": ".token",
    "parse_token_account": ".token",
    "parse_url": ".solana_pay",
    "validate_transfer": ".solana_pay",
    "token_amount_to_base_units": ".token",
    "transfer_checked": ".token",
}


def __getattr__(name: str) -> Any:
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})


__all__ = [
    "ASSOCIATED_TOKEN_PROGRAM_ID",
    "AddressLookupTableAccount",
    "AsyncClient",
    "Client",
    "Keypair",
    "MessageAddressTableLookup",
    "MessageV0",
    "MessageV1",
    "NonceInformation",
    "PrivateKey",
    "PublicKey",
    "Transaction",
    "TransactionConfig",
    "TOKEN_2022_PROGRAM_ID",
    "TOKEN_PROGRAM_ID",
    "TokenAccount",
    "TokenExtensionType",
    "TokenMint",
    "UnsupportedTokenExtensionError",
    "VersionedTransaction",
    "create_qr",
    "create_associated_token_account",
    "create_transfer",
    "encode_url",
    "fetch_transaction",
    "find_reference",
    "get_associated_token_address",
    "parse_mint",
    "parse_token_account",
    "parse_url",
    "validate_transfer",
    "token_amount_to_base_units",
    "transfer_checked",
]
