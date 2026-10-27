"""Invoice arithmetic using integer cents."""

TAX_RATES = {"FR": 20, "DE": 19, "US": 0}


def tax_for(amount_cents, country):
    """Tax in cents for an amount; unknown countries raise KeyError."""
    return amount_cents * TAX_RATES[country] // 100


def apply_discount(amount_cents, percent):
    """Amount after a percentage discount (0 to 100)."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return amount_cents - amount_cents * percent // 100


def compute_total(items, country, discount_percent=0):
    """Total in cents for (unit_price_cents, quantity) items, discounted then taxed."""
    subtotal = sum(price * qty for price, qty in items)
    discounted = apply_discount(subtotal, discount_percent)
    return discounted + tax_for(discounted, country)


def format_invoice(items, country, discount_percent=0):
    """Plain-text invoice with one line per item and a total."""
    lines = [f"{qty} x {price / 100:.2f}" for price, qty in items]
    total = compute_total(items, country, discount_percent)
    lines.append(f"TOTAL {total / 100:.2f}")
    return "\n".join(lines)
