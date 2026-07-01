from typing import Annotated
from pydantic import validate_call, Field
from opentelemetry import trace
from tools.telemetry import get_tracer

tracer = get_tracer()


@tracer.start_as_current_span("process_payment")
@validate_call
def process_payment(
    amount: Annotated[
        float, Field(gt=0, description="The amount to pay in USD. Must be greater than 0.")
    ],
    item: Annotated[
        str, Field(min_length=1, description="The item being purchased.")
    ],
    merchant: Annotated[
        str, Field(min_length=1, description="The store or merchant name.")
    ],
) -> str:
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

