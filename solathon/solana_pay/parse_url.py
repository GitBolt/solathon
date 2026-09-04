from __future__ import annotations

import re
from decimal import Decimal
from urllib.parse import parse_qs, unquote, urlsplit

from ..publickey import PublicKey
from .encode_url import MAX_SOLANA_PAY_URL_LENGTH, SOL_DECIMALS, _validate_https_link
from .types import TransactionRequestURL, TransferRequestURL

_AMOUNT_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
_BAD_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def parse_url(url: str) -> TransactionRequestURL | TransferRequestURL:
    """Parse and validate a Solana Pay URL without losing decimal precision."""

    if not isinstance(url, str):
        raise TypeError("url must be a string")
    if len(url) > MAX_SOLANA_PAY_URL_LENGTH:
        raise ValueError(
            f"Solana Pay URL cannot exceed {MAX_SOLANA_PAY_URL_LENGTH} characters"
        )
    if _BAD_PERCENT_ESCAPE.search(url):
        raise ValueError("Solana Pay URL contains invalid percent encoding")

    parsed = urlsplit(url)
    if parsed.scheme != "solana":
        raise ValueError("Invalid protocol, expected solana:")
    if parsed.netloc:
        raise ValueError("Solana Pay URLs must not use an authority component")
    if not parsed.path:
        raise ValueError("Solana Pay URL is missing a path")
    if parsed.fragment:
        raise ValueError("Solana Pay URLs cannot contain fragments")

    try:
        path = unquote(parsed.path, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("Solana Pay URL path is not valid UTF-8") from error

    # A transfer recipient is base58, so ':' and '%' unambiguously identify a
    # transaction request (including its conditionally encoded form).
    if ":" in path or "%" in parsed.path:
        return parse_transaction_request_url(path, parsed.query)
    return parse_transfer_request_url(path, parsed.query)


def parse_transaction_request_url(
    link: str,
    query: str = "",
) -> TransactionRequestURL:
    _validate_https_link(link)
    values = _parse_query(query)
    return TransactionRequestURL(
        link=link,
        label=_single(values, "label"),
        message=_single(values, "message"),
    )


def parse_transfer_request_url(path: str, query: str = "") -> TransferRequestURL:
    try:
        recipient = PublicKey(path)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid recipient") from error

    values = _parse_query(query)
    spl_token_value = _single(values, "spl-token")
    try:
        spl_token = PublicKey(spl_token_value) if spl_token_value is not None else None
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid SPL token mint") from error

    amount_value = _single(values, "amount")
    amount = None
    if amount_value is not None:
        if not _AMOUNT_PATTERN.fullmatch(amount_value):
            raise ValueError("Invalid amount: expected a non-negative decimal number")
        amount = Decimal(amount_value)
        if spl_token is None and _decimal_places(amount_value) > SOL_DECIMALS:
            raise ValueError("SOL amount cannot contain more than 9 decimal places")

    references = []
    for value in values.get("reference", []):
        try:
            references.append(PublicKey(value))
        except (TypeError, ValueError) as error:
            raise ValueError("Invalid reference") from error

    return TransferRequestURL(
        recipient=recipient,
        amount=amount,
        label=_single(values, "label"),
        message=_single(values, "message"),
        memo=_single(values, "memo"),
        reference=references,
        spl_token=spl_token,
    )


def _parse_query(query: str) -> dict[str, list[str]]:
    try:
        return parse_qs(
            query,
            keep_blank_values=True,
            encoding="utf-8",
            errors="strict",
            max_num_fields=100,
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("Invalid Solana Pay query string") from error


def _single(values: dict[str, list[str]], key: str) -> str | None:
    entries = values.get(key)
    if not entries:
        return None
    if len(entries) != 1:
        raise ValueError(f"Solana Pay field '{key}' may only appear once")
    return entries[0]


def _decimal_places(value: str) -> int:
    return len(value.partition(".")[2])
