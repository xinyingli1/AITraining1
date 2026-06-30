from opentelemetry import trace
from tools.telemetry import get_tracer

tracer = get_tracer()


@tracer.start_as_current_span("process_payment")
def process_payment(amount: float, item: str, merchant: str) -> str:
    """Processes a payment for groceries, meal kits, or restaurant orders.

    CRITICAL: This tool involves spending money and requires explicit user confirmation.

    Args:
        amount: The amount to pay in USD (e.g., 45.50).
        item: The item being purchased (e.g., "Weekly Grocery List").
        merchant: The store or restaurant (e.g., "Whole Foods", "UberEats").

    Returns:
        A confirmation message of the transaction.
    """
    span = trace.get_current_span()
    span.set_attribute("payment.amount", amount)
    span.set_attribute("payment.item", item)
    span.set_attribute("payment.merchant", merchant)

    return f"SUCCESS: Payment of ${amount:.2f} to {merchant} for '{item}' was successfully processed."
