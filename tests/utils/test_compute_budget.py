from solathon.core.compute_budget import ComputeBudgetProgram

def test_set_compute_unit_limit():
    instruction = ComputeBudgetProgram.set_compute_unit_limit(1000)
    assert instruction.program_id == "ComputeBudget111111111111111111111111111111"
    assert instruction.data[0] == 0  # Tag for set_compute_unit_limit
    assert int.from_bytes(instruction.data[1:5], "little") == 1000

def test_set_compute_unit_price():
    instruction = ComputeBudgetProgram.set_compute_unit_price(10)
    assert instruction.program_id == "ComputeBudget111111111111111111111111111111"
    assert instruction.data[0] == 3  # Tag for set_compute_unit_price
    assert int.from_bytes(instruction.data[1:9], "little") == 10