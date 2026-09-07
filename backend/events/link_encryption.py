"""Authenticated public-link storage, separate from Django signing secrets."""

import hashlib
import hmac
import json
import re

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings


class LinkRecoveryError(Exception):
    def __init__(self, code="recovery_unavailable", status_code=503):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def _keyring() -> MultiFernet:
    try:
        keys = settings.PUBLIC_LINK_ENCRYPTION_KEYS
        if not isinstance(keys, (list, tuple)) or not keys:
            raise ValueError
        return MultiFernet([Fernet(key) for key in keys])
    except (ValueError, TypeError, AttributeError):
        raise LinkRecoveryError() from None


def encrypt_link_token(token: str, *, church_id: int, event_id: int) -> str:
    payload = json.dumps(
        {"token": token, "church_id": church_id, "event_id": event_id}
    ).encode("utf-8")
    return _keyring().encrypt(payload).decode("ascii")


def decrypt_link_token(link) -> str:
    try:
        payload = json.loads(_keyring().decrypt(link.encrypted_token.encode("ascii")))
        token = payload["token"]
        if (
            not isinstance(token, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token)
            or payload["church_id"] != link.church_id
            or payload["event_id"] != link.event_id
            or not hmac.compare_digest(
                hashlib.sha256(token.encode("utf-8")).hexdigest(), link.token_digest
            )
        ):
            raise ValueError
        return token
    except (
        InvalidToken,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        UnicodeError,
    ):
        raise LinkRecoveryError() from None
