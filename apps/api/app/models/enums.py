import enum


class UserRole(enum.StrEnum):
    USER = "user"
    ADMIN = "admin"


class SubscriptionStatus(enum.StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"


class PaymentStatus(enum.StrEnum):
    AWAITING_RECEIPT = "awaiting_receipt"  # created, user has not uploaded a receipt yet
    PENDING_REVIEW = "pending_review"  # receipt uploaded, waiting for admin
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class PaymentMethod(enum.StrEnum):
    ALIF = "alif"
    DUSHANBE_CITY = "dushanbe_city"
