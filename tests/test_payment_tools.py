from tools import payment_tools


def test_process_payment():
    amount = 45.50
    item = "Weekly Groceries"
    merchant = "Whole Foods"

    result = payment_tools.process_payment(amount, item, merchant)

    assert "SUCCESS" in result
    assert "$45.50" in result
    assert "Whole Foods" in result
    assert "Weekly Groceries" in result


def test_process_payment_invalid_arguments():
    import pytest
    from pydantic import ValidationError

    # Test invalid amount (<= 0)
    with pytest.raises(ValidationError):
        payment_tools.process_payment(-10.0, "Groceries", "Whole Foods")

    # Test empty item
    with pytest.raises(ValidationError):
        payment_tools.process_payment(10.0, "", "Whole Foods")

    # Test empty merchant
    with pytest.raises(ValidationError):
        payment_tools.process_payment(10.0, "Groceries", "")

