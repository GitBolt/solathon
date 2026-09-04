from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import NotRequired, Required, TypedDict

from ..publickey import PublicKey

Amount = Decimal | int | float | str


class CreateTransferFields(TypedDict):
    recipient: Required[PublicKey]
    amount: Required[Amount]
    reference: NotRequired[Sequence[PublicKey] | PublicKey]
    memo: NotRequired[str]
    spl_token: NotRequired[PublicKey]


@dataclass(frozen=True, slots=True)
class TransactionRequestURL:
    link: str
    label: str | None
    message: str | None


@dataclass(frozen=True, slots=True)
class TransferRequestURL:
    recipient: PublicKey
    amount: Decimal | None
    label: str | None
    message: str | None
    memo: str | None
    reference: list[PublicKey]
    spl_token: PublicKey | None
