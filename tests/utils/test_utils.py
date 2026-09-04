from decimal import Decimal

import pytest

from solathon import utils


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, 0),
        (1, 1_000_000_000),
        (1.0, 1_000_000_000),
        ("123.123", 123_123_000_000),
        (Decimal("0.000000001"), 1),
    ],
)
def test_sol_to_lamport_is_exact(amount, expected):
    assert utils.sol_to_lamport(amount) == expected


@pytest.mark.parametrize("amount", [None, True, object()])
def test_sol_to_lamport_rejects_non_numeric_values(amount):
    with pytest.raises(TypeError):
        utils.sol_to_lamport(amount)


@pytest.mark.parametrize("amount", [-1, "nan", "inf", "0.0000000001"])
def test_sol_to_lamport_rejects_invalid_values(amount):
    with pytest.raises(ValueError):
        utils.sol_to_lamport(amount)


def test_lamport_to_sol_has_exact_decimal_variant():
    assert utils.lamport_to_sol(1_000_000_001) == 1.000000001
    assert utils.lamport_to_sol_decimal(1_000_000_001) == Decimal("1.000000001")


@pytest.mark.parametrize("amount", [None, 1.5, True])
def test_lamport_to_sol_requires_integer_lamports(amount):
    with pytest.raises(TypeError):
        utils.lamport_to_sol(amount)


def test_lamport_values_must_fit_u64():
    with pytest.raises(ValueError):
        utils.lamport_to_sol(-1)
    with pytest.raises(ValueError):
        utils.sol_to_lamport(Decimal(2**64) / utils.LAMPORT_PER_SOL)
