from __future__ import annotations

from ..publickey import PublicKey
from .instructions import Instruction
from .layouts import encode_u32, encode_u64

COMPUTE_BUDGET_PROGRAM_ID = PublicKey("ComputeBudget111111111111111111111111111111")


def request_heap_frame(bytes_: int) -> Instruction:
    return Instruction(
        keys=[],
        program_id=COMPUTE_BUDGET_PROGRAM_ID,
        data=bytes([1]) + encode_u32(bytes_, "bytes"),
    )


def set_compute_unit_limit(units: int) -> Instruction:
    return Instruction(
        keys=[],
        program_id=COMPUTE_BUDGET_PROGRAM_ID,
        data=bytes([2]) + encode_u32(units, "units"),
    )


def set_compute_unit_price(micro_lamports: int) -> Instruction:
    return Instruction(
        keys=[],
        program_id=COMPUTE_BUDGET_PROGRAM_ID,
        data=bytes([3]) + encode_u64(micro_lamports, "micro_lamports"),
    )


def set_loaded_accounts_data_size_limit(bytes_: int) -> Instruction:
    return Instruction(
        keys=[],
        program_id=COMPUTE_BUDGET_PROGRAM_ID,
        data=bytes([4]) + encode_u32(bytes_, "bytes"),
    )


class ComputeBudgetProgram:
    """Backward-compatible namespace for compute-budget instructions."""

    request_heap_frame = staticmethod(request_heap_frame)
    set_compute_unit_limit = staticmethod(set_compute_unit_limit)
    set_compute_unit_price = staticmethod(set_compute_unit_price)
    set_loaded_accounts_data_size_limit = staticmethod(
        set_loaded_accounts_data_size_limit
    )
