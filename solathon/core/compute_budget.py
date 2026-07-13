from __future__ import annotations

from ..publickey import PublicKey
from .instructions import Instruction


COMPUTE_BUDGET_PROGRAM_ID = PublicKey(
    "ComputeBudget111111111111111111111111111111"
)


class ComputeBudgetProgram:
    """Creates instructions for setting a transaction's compute budget."""

    @staticmethod
    def set_compute_unit_limit(units: int) -> Instruction:
        """Sets the maximum compute units available to the transaction."""
        if not 0 <= units <= 0xFFFFFFFF:
            raise ValueError("Compute unit limit must fit in an unsigned 32-bit integer")
        return Instruction(
            keys=[],
            program_id=COMPUTE_BUDGET_PROGRAM_ID,
            data=bytes([2]) + units.to_bytes(4, "little"),
        )

    @staticmethod
    def set_compute_unit_price(micro_lamports: int) -> Instruction:
        """Sets the additional fee in micro-lamports per compute unit."""
        if not 0 <= micro_lamports <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError("Compute unit price must fit in an unsigned 64-bit integer")
        return Instruction(
            keys=[],
            program_id=COMPUTE_BUDGET_PROGRAM_ID,
            data=bytes([3]) + micro_lamports.to_bytes(8, "little"),
        )
