from __future__ import annotations

from collections.abc import Iterable

from ..publickey import PublicKey
from .instructions import AccountMeta, Instruction


def ordered_account_metas(
    fee_payer: PublicKey,
    instructions: Iterable[Instruction],
    signer_public_keys: Iterable[PublicKey] = (),
) -> list[AccountMeta]:
    metas: dict[PublicKey, AccountMeta] = {}

    def add_meta(meta: AccountMeta) -> None:
        public_key = (
            PublicKey(bytes(meta.public_key))
            if isinstance(meta.public_key, PublicKey)
            else PublicKey(meta.public_key)
        )
        current = metas.get(public_key)
        if current is None:
            metas[public_key] = AccountMeta(
                public_key=public_key,
                is_signer=meta.is_signer,
                is_writable=meta.is_writable,
            )
            return
        current.is_signer = current.is_signer or meta.is_signer
        current.is_writable = current.is_writable or meta.is_writable

    instruction_list = list(instructions)
    for instruction in instruction_list:
        for meta in instruction.keys:
            add_meta(meta)
        add_meta(AccountMeta(instruction.program_id, False, False))

    for public_key in signer_public_keys:
        add_meta(AccountMeta(public_key, True, False))

    add_meta(AccountMeta(fee_payer, True, True))
    payer_meta = metas.pop(fee_payer)
    ordered = sorted(
        metas.values(),
        key=lambda meta: (not meta.is_signer, not meta.is_writable),
    )
    return [payer_meta, *ordered]
