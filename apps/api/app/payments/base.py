"""PaymentProvider: how a user pays. MVP has only manual transfer + receipt."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from app.models import PaymentMethod


@dataclass(frozen=True, slots=True)
class BankLink:
    code: str  # alif | dc | sber | tbank: the web app shows the bank name by this code
    url: str


@dataclass(frozen=True, slots=True)
class PaymentInstructions:
    method: PaymentMethod
    account_kind: Literal["phone", "card"]
    account: str
    recipient: str
    fee_percent: int = 0
    banks: tuple[BankLink, ...] = field(default_factory=tuple)


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def methods(self) -> list[PaymentInstructions]:
        """Methods the user can choose, with what to show them."""

    @property
    @abstractmethod
    def requires_receipt(self) -> bool:
        """True when an admin must confirm the payment from an uploaded receipt."""
