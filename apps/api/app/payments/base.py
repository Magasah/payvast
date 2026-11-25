"""PaymentProvider: how a user pays. MVP has only manual transfer + receipt."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models import PaymentMethod


@dataclass(frozen=True, slots=True)
class PaymentInstructions:
    method: PaymentMethod
    wallet: str


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def methods(self) -> list[PaymentInstructions]:
        """Methods the user can choose, with what to show them."""

    @property
    @abstractmethod
    def requires_receipt(self) -> bool:
        """True when an admin must confirm the payment from an uploaded receipt."""
