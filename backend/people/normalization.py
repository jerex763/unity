import re


def normalize_email(value: str | None) -> str | None:
    """Return the stable comparison form used for tenant-local identity matching."""
    normalized = (value or "").strip().casefold()
    return normalized or None


def normalize_phone(value: str | None) -> str | None:
    """Normalize formatting without guessing a country or changing the number."""
    normalized = re.sub(r"\D", "", value or "")
    if normalized.startswith("00"):
        normalized = normalized[2:]
    return normalized or None


def normalize_wechat_id(value: str | None) -> str | None:
    """Return the tenant-local comparison form for a WeChat identifier."""
    normalized = (value or "").strip().casefold()
    return normalized or None
