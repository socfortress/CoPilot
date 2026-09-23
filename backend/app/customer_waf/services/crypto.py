"""
Encryption of WAF service tokens at rest.

A `wafst_…` token is a bearer credential CoPilot has to *send*, so it can't be
hashed — it is Fernet-encrypted with ``WAF_TOKEN_ENCRYPTION_KEY``.

The key is deliberately dedicated and has **no fallback** (#1165):

- Not ``TOTP_ENCRYPTION_KEY``: rotating one must never make the other's stored
  secrets unreadable.
- Not derived from ``JWT_SECRET`` (the TOTP key's fallback): that would tie every
  stored WAF token to JWT rotation, the same lock-in by another route.

Without the key, saving a WAF is refused with an actionable message. Rotating it
makes stored tokens undecryptable; recovery is re-entering each token (cheap —
tokens are issued in the WAF UI), which is why decryption failure is reported as
its own error rather than as a WAF authentication failure.

The key is read from the environment on each call rather than at import, so a key
added to ``.env`` needs only a restart and tests can set it per case.
"""

import os

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

KEY_ENV_VAR = "WAF_TOKEN_ENCRYPTION_KEY"
TOKEN_PREFIX = "wafst_"
# Shown in the UI in place of the token: enough to tell tokens apart, not enough to use one.
DISPLAY_PREFIX_LENGTH = 12

KEY_GENERATE_HINT = 'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'


class WafTokenCryptoError(Exception):
    """Base class. ``status_code`` is what a route should answer with."""

    status_code = 400


class WafKeyNotConfiguredError(WafTokenCryptoError):
    pass


class WafKeyMalformedError(WafTokenCryptoError):
    pass


class WafTokenUndecryptableError(WafTokenCryptoError):
    # 409: the stored row is fine structurally but unusable until an admin re-enters the token.
    status_code = 409


class InvalidWafTokenError(WafTokenCryptoError):
    pass


def _fernet() -> Fernet:
    raw = (os.environ.get(KEY_ENV_VAR) or "").strip()
    if not raw or raw == "REPLACE_ME":
        raise WafKeyNotConfiguredError(f"{KEY_ENV_VAR} is not set, so WAF tokens cannot be stored or used. {KEY_GENERATE_HINT}")
    try:
        return Fernet(raw.encode())
    except (ValueError, TypeError) as e:
        raise WafKeyMalformedError(
            f"{KEY_ENV_VAR} is malformed: expected a 32-byte url-safe base64 Fernet key (44 characters ending in '='). "
            f"{KEY_GENERATE_HINT}",
        ) from e


def key_configured() -> bool:
    """Whether a usable key is present — lets the UI explain a disabled form up front."""
    try:
        _fernet()
    except WafTokenCryptoError:
        return False
    return True


def normalize_token(token: str) -> str:
    """Validate a pasted service token and return it trimmed.

    Only WAF service tokens are accepted: a pasted WAF login JWT would expire within the
    hour, and a gateway API key (``waf_…``) never authenticates to the admin API at all.
    """
    token = (token or "").strip()
    if not token.startswith(TOKEN_PREFIX) or len(token) <= len(TOKEN_PREFIX):
        raise InvalidWafTokenError(
            f"Not a WAF service token: expected a value starting with '{TOKEN_PREFIX}' "
            "(WAF → Service Tokens). WAF login tokens and site API keys don't work here.",
        )
    return token


def display_prefix(token: str) -> str:
    return token[:DISPLAY_PREFIX_LENGTH] + "..."


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(normalize_token(token).encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise WafTokenUndecryptableError(
            f"The stored WAF token can't be decrypted — {KEY_ENV_VAR} has changed since it was saved. Re-enter the token for this WAF.",
        ) from e
