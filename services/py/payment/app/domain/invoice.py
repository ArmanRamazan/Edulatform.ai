from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True)
class InvoiceData:
    invoice_number: str
    payment_date: datetime
    buyer_name: str
    buyer_email: str
    course_title: str
    original_price: Decimal
    discount_amount: Decimal
    final_price: Decimal
    coupon_code: str | None


def generate_invoice_number() -> str:
    year = datetime.now(timezone.utc).year
    digits = random.randint(0, 999999)
    return f"INV-{year}-{digits:06d}"
