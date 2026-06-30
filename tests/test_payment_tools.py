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
