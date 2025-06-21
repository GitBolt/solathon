from solathon.core.instructions import Instruction

COMPUTE_BUDGET_PROGRAM_ID = "ComputeBudget111111111111111111111111111111"

class ComputeBudgetProgram:
    @staticmethod
    def set_compute_unit_limit(units: int) -> Instruction:
        # 0 = tag for set compute unit limit
        data = bytes([0]) + units.to_bytes(4, "little")
        return Instruction(
            program_id=COMPUTE_BUDGET_PROGRAM_ID,
            accounts=[],
            data=data
        )

    @staticmethod
    def set_compute_unit_price(micro_lamports: int) -> Instruction:
        # 3 = tag for set compute unit price
        data = bytes([3]) + micro_lamports.to_bytes(8, "little")
        return Instruction(
            program_id=COMPUTE_BUDGET_PROGRAM_ID,
            accounts=[],
            data=data
        )