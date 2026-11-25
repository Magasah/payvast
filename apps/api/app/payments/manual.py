from app.config import get_settings
from app.models import PaymentMethod
from app.payments.base import BankLink, PaymentInstructions, PaymentProvider

# Public bank web addresses. On phones with the bank app installed, the OS may open the app.
ALIF = BankLink("alif", "https://app.alif.tj/")
DC = BankLink("dc", "https://next.dc.tj/")
SBER = BankLink("sber", "https://online.sberbank.ru/")
TBANK = BankLink("tbank", "https://www.tbank.ru/mybank/")


class ManualPaymentProvider(PaymentProvider):
    """User transfers money (Alif, Dushanbe City, card) and uploads a receipt."""

    name = "manual"

    def methods(self) -> list[PaymentInstructions]:
        s = get_settings()
        candidates = [
            PaymentInstructions(
                PaymentMethod.ALIF,
                "phone",
                s.payment_alif_account,
                s.payment_alif_recipient,
                banks=(ALIF,),
            ),
            PaymentInstructions(
                PaymentMethod.DUSHANBE_CITY,
                "phone",
                s.payment_dc_account,
                s.payment_dc_recipient,
                fee_percent=s.payment_dc_fee_percent,
                banks=(DC,),
            ),
            PaymentInstructions(
                PaymentMethod.CARD,
                "card",
                s.payment_card_number,
                s.payment_card_recipient,
                banks=(SBER, TBANK),
            ),
        ]
        return [m for m in candidates if m.account]

    def is_enabled(self, method: PaymentMethod) -> bool:
        return any(m.method == method for m in self.methods())

    @property
    def requires_receipt(self) -> bool:
        return True
