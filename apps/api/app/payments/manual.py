from app.config import get_settings
from app.models import PaymentMethod
from app.payments.base import PaymentInstructions, PaymentProvider


class ManualPaymentProvider(PaymentProvider):
    """User transfers money to a wallet (Alif / Dushanbe City) and uploads a receipt."""

    name = "manual"

    def methods(self) -> list[PaymentInstructions]:
        settings = get_settings()
        wallets = {
            PaymentMethod.ALIF: settings.payment_wallet_alif,
            PaymentMethod.DUSHANBE_CITY: settings.payment_wallet_dc,
        }
        return [PaymentInstructions(m, w) for m, w in wallets.items() if w]

    @property
    def requires_receipt(self) -> bool:
        return True
