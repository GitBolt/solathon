from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from ..publickey import PublicKey
from .layouts import (
    SYSTEM_PROGRAM_ID,
    SYSVAR_RECENT_BLOCKHASHES_ID,
    SYSVAR_RENT_ID,
    InstructionType,
    encode_system_instruction,
)

MEMO_PROGRAM_ID = PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")


@dataclass
class AccountMeta:
    public_key: PublicKey | str
    is_signer: bool
    is_writable: bool

    def __post_init__(self) -> None:
        if isinstance(self.public_key, str):
            self.public_key = PublicKey(self.public_key)


class Instruction(NamedTuple):
    keys: list[AccountMeta]
    program_id: PublicKey
    data: bytes = bytes(0)

    def _to_json(self):
        return {
            "keys": [
                {
                    "pubkey": str(key.public_key),
                    "isSigner": key.is_signer,
                    "isWritable": key.is_writable,
                }
                for key in self.keys
            ],
            "programId": str(self.program_id),
            "data": list(self.data),
        }


def create_memo(
    memo: str,
    signer_public_keys: list[PublicKey] | None = None,
) -> Instruction:
    if not isinstance(memo, str):
        raise TypeError("memo must be a string")
    memo_data = memo.encode("utf-8")
    if not memo_data:
        raise ValueError("memo cannot be empty")
    return Instruction(
        keys=[
            AccountMeta(public_key, is_signer=True, is_writable=False)
            for public_key in signer_public_keys or []
        ],
        program_id=MEMO_PROGRAM_ID,
        data=memo_data,
    )


def create_account(
    from_public_key: PublicKey,
    new_account_public_key: PublicKey,
    lamports: int,
    space: int,
    program_id: PublicKey,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(from_public_key, is_signer=True, is_writable=True),
            AccountMeta(new_account_public_key, is_signer=True, is_writable=True),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.CREATE_ACCOUNT,
            lamports=lamports,
            space=space,
            program_id=program_id,
        ),
    )


def create_account_with_seed(
    from_public_key: PublicKey,
    new_account_public_key: PublicKey,
    base_public_key: PublicKey,
    seed: str,
    lamports: int,
    space: int,
    program_id: PublicKey,
) -> Instruction:
    keys = [
        AccountMeta(from_public_key, is_signer=True, is_writable=True),
        AccountMeta(new_account_public_key, is_signer=False, is_writable=True),
    ]
    if base_public_key != from_public_key:
        keys.append(AccountMeta(base_public_key, is_signer=True, is_writable=False))
    return Instruction(
        keys=keys,
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.CREATE_ACCOUNT_WITH_SEED,
            base=base_public_key,
            seed=seed,
            lamports=lamports,
            space=space,
            program_id=program_id,
        ),
    )


def assign(account_public_key: PublicKey, program_id: PublicKey) -> Instruction:
    return Instruction(
        keys=[AccountMeta(account_public_key, is_signer=True, is_writable=True)],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.ASSIGN,
            program_id=program_id,
        ),
    )


def assign_with_seed(
    account_public_key: PublicKey,
    base_public_key: PublicKey,
    seed: str,
    program_id: PublicKey,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(account_public_key, is_signer=False, is_writable=True),
            AccountMeta(base_public_key, is_signer=True, is_writable=False),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.ASSIGN_WITH_SEED,
            base=base_public_key,
            seed=seed,
            program_id=program_id,
        ),
    )


def transfer(
    from_public_key: PublicKey | str,
    to_public_key: PublicKey | str,
    lamports: int,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(from_public_key, is_signer=True, is_writable=True),
            AccountMeta(to_public_key, is_signer=False, is_writable=True),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.TRANSFER,
            lamports=lamports,
        ),
    )


def transfer_with_seed(
    from_public_key: PublicKey,
    base_public_key: PublicKey,
    from_seed: str,
    from_owner: PublicKey,
    to_public_key: PublicKey,
    lamports: int,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(from_public_key, is_signer=False, is_writable=True),
            AccountMeta(base_public_key, is_signer=True, is_writable=False),
            AccountMeta(to_public_key, is_signer=False, is_writable=True),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.TRANSFER_WITH_SEED,
            lamports=lamports,
            from_seed=from_seed,
            from_owner=from_owner,
        ),
    )


def allocate(account_public_key: PublicKey, space: int) -> Instruction:
    return Instruction(
        keys=[AccountMeta(account_public_key, is_signer=True, is_writable=True)],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.ALLOCATE,
            space=space,
        ),
    )


def allocate_with_seed(
    account_public_key: PublicKey,
    base_public_key: PublicKey,
    seed: str,
    space: int,
    program_id: PublicKey,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(account_public_key, is_signer=False, is_writable=True),
            AccountMeta(base_public_key, is_signer=True, is_writable=False),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.ALLOCATE_WITH_SEED,
            base=base_public_key,
            seed=seed,
            space=space,
            program_id=program_id,
        ),
    )


def advance_nonce_account(
    nonce_public_key: PublicKey,
    authority_public_key: PublicKey,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(nonce_public_key, is_signer=False, is_writable=True),
            AccountMeta(
                SYSVAR_RECENT_BLOCKHASHES_ID, is_signer=False, is_writable=False
            ),
            AccountMeta(authority_public_key, is_signer=True, is_writable=False),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(InstructionType.ADVANCE_NONCE_ACCOUNT),
    )


def withdraw_nonce_account(
    nonce_public_key: PublicKey,
    recipient_public_key: PublicKey,
    authority_public_key: PublicKey,
    lamports: int,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(nonce_public_key, is_signer=False, is_writable=True),
            AccountMeta(recipient_public_key, is_signer=False, is_writable=True),
            AccountMeta(
                SYSVAR_RECENT_BLOCKHASHES_ID, is_signer=False, is_writable=False
            ),
            AccountMeta(SYSVAR_RENT_ID, is_signer=False, is_writable=False),
            AccountMeta(authority_public_key, is_signer=True, is_writable=False),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.WITHDRAW_NONCE_ACCOUNT,
            lamports=lamports,
        ),
    )


def initialize_nonce_account(
    nonce_public_key: PublicKey,
    authority_public_key: PublicKey,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(nonce_public_key, is_signer=False, is_writable=True),
            AccountMeta(
                SYSVAR_RECENT_BLOCKHASHES_ID, is_signer=False, is_writable=False
            ),
            AccountMeta(SYSVAR_RENT_ID, is_signer=False, is_writable=False),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.INITIALIZE_NONCE_ACCOUNT,
            authorized=authority_public_key,
        ),
    )


def authorize_nonce_account(
    nonce_public_key: PublicKey,
    authority_public_key: PublicKey,
    new_authority_public_key: PublicKey,
) -> Instruction:
    return Instruction(
        keys=[
            AccountMeta(nonce_public_key, is_signer=False, is_writable=True),
            AccountMeta(authority_public_key, is_signer=True, is_writable=False),
        ],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.AUTHORIZE_NONCE_ACCOUNT,
            authorized=new_authority_public_key,
        ),
    )


def upgrade_nonce_account(nonce_public_key: PublicKey) -> Instruction:
    """Upgrade a legacy durable-nonce account to the current format."""

    return Instruction(
        keys=[AccountMeta(nonce_public_key, is_signer=False, is_writable=True)],
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(InstructionType.UPGRADE_NONCE_ACCOUNT),
    )


def create_account_allow_prefund(
    new_account_public_key: PublicKey,
    lamports: int,
    space: int,
    program_id: PublicKey,
    payer_public_key: PublicKey | None = None,
) -> Instruction:
    """Create an account even when its address already holds lamports.

    If ``payer_public_key`` is omitted, the destination must already be
    sufficiently funded and the instruction encodes a funding amount of zero.
    This instruction requires a current Agave runtime that supports system
    instruction 13.
    """

    keys = [AccountMeta(new_account_public_key, is_signer=True, is_writable=True)]
    if payer_public_key is not None:
        keys.append(AccountMeta(payer_public_key, is_signer=True, is_writable=True))
    return Instruction(
        keys=keys,
        program_id=SYSTEM_PROGRAM_ID,
        data=encode_system_instruction(
            InstructionType.CREATE_ACCOUNT_ALLOW_PREFUND,
            lamports=lamports if payer_public_key is not None else 0,
            space=space,
            program_id=program_id,
        ),
    )
