from app.payments.base import PaymentInstructions, PaymentProvider
from app.payments.manual import ManualPaymentProvider


def get_payment_provider() -> PaymentProvider:
    return ManualPaymentProvider()


__all__ = [
    "ManualPaymentProvider",
    "PaymentInstructions",
    "PaymentProvider",
    "get_payment_provider",
]
