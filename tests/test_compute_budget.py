import pytest

from solathon import PublicKey
from solathon.core import ComputeBudgetProgram
from solathon.core.instructions import transfer


def test_set_compute_unit_limit():
    instruction = ComputeBudgetProgram.set_compute_unit_limit(200000)

    assert instruction.keys == []
    assert str(instruction.program_id) == "ComputeBudget111111111111111111111111111111"
    assert instruction.data == bytes([2]) + (200000).to_bytes(4, "little")


def test_set_compute_unit_price():
    instruction = ComputeBudgetProgram.set_compute_unit_price(1000)

    assert instruction.keys == []
    assert instruction.data == bytes([3]) + (1000).to_bytes(8, "little")


def test_compute_budget_values_must_fit_their_wire_types():
    with pytest.raises(ValueError):
        ComputeBudgetProgram.set_compute_unit_limit(-1)

    with pytest.raises(ValueError):
        ComputeBudgetProgram.set_compute_unit_price(2 ** 64)


def test_transfer_keeps_the_existing_system_instruction_encoding():
    sender = PublicKey(bytes(range(32)))
    receiver = PublicKey(bytes(range(1, 33)))
    instruction = transfer(sender, receiver, 1000)

    assert instruction.data == bytes([2, 0, 0, 0]) + (1000).to_bytes(8, "little")
