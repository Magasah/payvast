from datetime import datetime


def format_tjs(dirams: int) -> str:
    """5000 -> '50.00 TJS'. Prices are integer dirams (1 somoni = 100 dirams)."""
    return f"{dirams // 100}.{dirams % 100:02d} TJS"


def format_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")
