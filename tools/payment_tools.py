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
    return f"SUCCESS: Payment of ${amount:.2f} to {merchant} for '{item}' was successfully processed."
