import pytest
from solathon import utils


def get_rounded_expectation(arg):
    return utils.truncate_float(arg * utils.SOL_PER_LAMPORT, utils.SOL_FLOATING_PRECISION)


sol_to_lamport_test_data = [
    (0, 0),
    (0.0, 0),
    (1.0, 1000000000),
    (2.0, int(2 * utils.LAMPORT_PER_SOL)),
    (99999.0, int(99999 * utils.LAMPORT_PER_SOL)),
    (123.123, int(123.123 * utils.LAMPORT_PER_SOL)),
    (123123123123.123123123123, int(123123123123.123123123123 * utils.LAMPORT_PER_SOL))
]

lamport_to_sol_test_data = [
    (0, get_rounded_expectation(0)),
    (1, get_rounded_expectation(1)),
    (2, get_rounded_expectation(2)),
    (999999999, get_rounded_expectation(999999999)),
    (9999.999, get_rounded_expectation(9999.999)),
]


@pytest.mark.parametrize("arg, expected", sol_to_lamport_test_data)
def test_sol_to_lamport(arg, expected):
    actual = utils.sol_to_lamport(arg)
    assert actual == expected
    assert isinstance(actual, int)


def test_sol_to_lamport_none_passed_in():
    with pytest.raises(TypeError):
        utils.sol_to_lamport(None)


@pytest.mark.parametrize("arg, expected", [(-arg, -expected) for arg, expected in sol_to_lamport_test_data])
def test_sol_to_lamport_negative_input(arg, expected):
    actual = utils.sol_to_lamport(arg)
    assert actual == expected
    assert isinstance(actual, int)


def test_sol_to_lamport_large_input():
    i = 99999999999999999999999999999.99999999999999999999999999999999
    assert utils.sol_to_lamport(i) == int(i * utils.LAMPORT_PER_SOL)


@pytest.mark.parametrize("arg, expected", lamport_to_sol_test_data)
def test_lamport_to_sol(arg, expected):
    actual = utils.lamport_to_sol(arg)
    assert actual == expected
    assert isinstance(actual, float)


def test_lamport_to_sol_none_passed_in():
    with pytest.raises(TypeError):
        utils.lamport_to_sol(None)


@pytest.mark.parametrize("arg, expected", [(-arg, -expected) for arg, expected in lamport_to_sol_test_data])
def test_lamport_to_sol_negative_input(arg, expected):
    actual = utils.lamport_to_sol(arg)
    assert actual == expected
    assert isinstance(actual, float)


def test_lamport_to_sol_large_input():
    arg = 99999999999999999999999999999999999999999
    expected = get_rounded_expectation(arg)
    assert utils.lamport_to_sol(arg) == expected
    assert isinstance(expected, float)
