from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Any, TypedDict
from urllib.parse import quote, urlencode, urlsplit

from ..publickey import PublicKey

MAX_SOLANA_PAY_URL_LENGTH = 2048
SOL_DECIMALS = 9


class TransactionRequestURLParams(TypedDict, total=False):
    link: str
    label: str
    message: str


class TransferRequestURLParams(TypedDict, total=False):
    recipient: PublicKey | str
    amount: Decimal | int | float | str
    spl_token: PublicKey | str
    label: str
    message: str
    memo: str
    reference: Sequence[PublicKey | str] | PublicKey | str


def encode_url(
    data: TransactionRequestURLParams | TransferRequestURLParams | None = None,
    **fields: Any,
) -> str:
    """Encode a Solana Pay transfer or transaction-request URL.

    ``amount`` is always rendered as ordinary fixed-point decimal text. This
    prevents Python floats and :class:`~decimal.Decimal` values from leaking
    scientific notation into a URL, which the Solana Pay grammar prohibits.
    """

    values: dict[str, Any] = dict(data or {})
    values.update(fields)
    unknown = set(values) - {
        "link",
        "recipient",
        "amount",
        "spl_token",
        "label",
        "message",
        "memo",
        "reference",
    }
    if unknown:
        names = ", ".join(sorted(unknown))
        raise TypeError(f"Unknown Solana Pay field(s): {names}")
    if "link" in values and "recipient" in values:
        raise ValueError("A URL cannot contain both link and recipient")
    if "link" in values:
        transfer_only = {"amount", "spl_token", "memo", "reference"} & values.keys()
        if transfer_only:
            names = ", ".join(sorted(transfer_only))
            raise ValueError(f"Transaction request cannot contain: {names}")
        return encode_transaction_request_url(
            str(values["link"]),
            values.get("label"),
            values.get("message"),
        )
    if "recipient" not in values:
        raise ValueError("Recipient is missing from data")
    return encode_transfer_request_url(
        recipient=values["recipient"],
        amount=values.get("amount"),
        spl_token=values.get("spl_token"),
        label=values.get("label"),
        message=values.get("message"),
        memo=values.get("memo"),
        reference=values.get("reference"),
    )


def encode_transaction_request_url(
    link: str,
    label: str | None = None,
    message: str | None = None,
) -> str:
    _validate_https_link(link)

    # Per the specification, a link only needs to be encoded when its own
    # query would otherwise be confused with Solana Pay protocol parameters.
    pathname = quote(link, safe="") if "?" in link or "%" in link else link
    params: list[tuple[str, str]] = []
    if label is not None:
        params.append(("label", _text(label, "label")))
    if message is not None:
        params.append(("message", _text(message, "message")))
    return _bounded_url(f"solana:{pathname}", params)


def encode_transfer_request_url(
    recipient: PublicKey | str,
    amount: Decimal | int | float | str | None = None,
    spl_token: PublicKey | str | None = None,
    label: str | None = None,
    message: str | None = None,
    memo: str | None = None,
    reference: Sequence[PublicKey | str] | PublicKey | str | None = None,
) -> str:
    recipient_key = _public_key(recipient, "recipient")
    token_key = _public_key(spl_token, "spl_token") if spl_token is not None else None

    params: list[tuple[str, str]] = []
    if amount is not None:
        amount_text = _format_amount(amount)
        if token_key is None and _decimal_places(amount_text) > SOL_DECIMALS:
            raise ValueError("SOL amount cannot contain more than 9 decimal places")
        params.append(("amount", amount_text))
    if token_key is not None:
        params.append(("spl-token", str(token_key)))
    if reference is not None:
        references: Sequence[PublicKey | str]
        if isinstance(reference, (PublicKey, str)):
            references = [reference]
        elif isinstance(reference, Sequence):
            references = reference
        else:
            raise TypeError("reference must be a public key or a sequence of keys")
        params.extend(
            ("reference", str(_public_key(value, "reference"))) for value in references
        )
    if label is not None:
        params.append(("label", _text(label, "label")))
    if message is not None:
        params.append(("message", _text(message, "message")))
    if memo is not None:
        params.append(("memo", _text(memo, "memo")))
    return _bounded_url(f"solana:{recipient_key}", params)


def _format_amount(amount: Decimal | int | float | str) -> str:
    if isinstance(amount, bool):
        raise TypeError("amount must be a decimal number")
    if isinstance(amount, str) and amount != amount.strip():
        raise ValueError("amount cannot contain surrounding whitespace")
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("amount must be a decimal number") from error
    if not value.is_finite() or value < 0:
        raise ValueError("amount must be a non-negative finite number")
    if value == 0:
        return "0"
    if abs(value.adjusted()) > MAX_SOLANA_PAY_URL_LENGTH:
        raise ValueError("amount is too large for a Solana Pay URL")
    text = format(value, "f")
    if len(text) > MAX_SOLANA_PAY_URL_LENGTH:
        raise ValueError("amount is too precise for a Solana Pay URL")
    return text


def _decimal_places(value: str) -> int:
    return len(value.partition(".")[2])


def _bounded_url(base: str, params: list[tuple[str, str]]) -> str:
    query = urlencode(params, doseq=True, quote_via=quote, safe="")
    url = base + (f"?{query}" if query else "")
    if len(url) > MAX_SOLANA_PAY_URL_LENGTH:
        raise ValueError(
            f"Solana Pay URL cannot exceed {MAX_SOLANA_PAY_URL_LENGTH} characters"
        )
    return url


def _public_key(value: PublicKey | str, field: str) -> PublicKey:
    if isinstance(value, PublicKey):
        return value
    try:
        return PublicKey(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field}") from error


def _text(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    return value


def _validate_https_link(link: str) -> None:
    if not isinstance(link, str):
        raise TypeError("link must be a string")
    if any(ord(character) < 0x20 or character.isspace() for character in link):
        raise ValueError("Transaction request link contains whitespace or controls")
    parsed = urlsplit(link)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Transaction request links must use absolute HTTPS URLs")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Transaction request links cannot contain credentials")
    if parsed.fragment:
        raise ValueError("Transaction request links cannot contain fragments")
    try:
        _ = parsed.port
    except ValueError as error:
        raise ValueError("Transaction request link has an invalid port") from error
