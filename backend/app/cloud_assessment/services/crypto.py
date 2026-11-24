"""Encryption of cloud credentials at rest (#1328).

A cloud account's credential (AWS access keys, an Azure or Microsoft 365 client secret, a
GCP service-account key) is something CoPilot has to *send* to copilot-prowler, so it
can't be hashed: it is stored as one Fernet ciphertext of its JSON, under
``CLOUD_ASSESSMENT_ENCRYPTION_KEY``.

The key is dedicated and has **no fallback**, like the WAF's (#1165): not the TOTP key and
not derived from ``JWT_SECRET``, so rotating either never makes stored credentials
unreadable. Without the key, saving a credential is refused with a message saying how to
make one. Rotating it makes stored credentials undecryptable; that is reported as its own
error (409, "re-enter the credential"), never as a cloud sign-in failure.

The key is read on each call, so a key added to ``.env`` needs only a restart and tests can
set it per case. Nothing here logs a credential or its ciphertext.
"""

import json
import os
from typing import Any
from typing import Dict

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

KEY_ENV_VAR = "CLOUD_ASSESSMENT_ENCRYPTION_KEY"
KEY_GENERATE_HINT = 'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'


class CredentialCryptoError(Exception):
    """Base class. ``status_code`` is what a route answers with."""

    status_code = 400


class KeyNotConfiguredError(CredentialCryptoError):
    pass


class KeyMalformedError(CredentialCryptoError):
    pass


class CredentialUndecryptableError(CredentialCryptoError):
    # 409: the row is fine, but unusable until an admin re-enters the credential.
    status_code = 409


def _fernet() -> Fernet:
    raw = (os.environ.get(KEY_ENV_VAR) or "").strip()
    if not raw or raw == "REPLACE_ME":
        raise KeyNotConfiguredError(f"{KEY_ENV_VAR} is not set, so cloud credentials can't be stored or used. {KEY_GENERATE_HINT}")
    try:
        return Fernet(raw.encode())
    except (ValueError, TypeError) as error:
        raise KeyMalformedError(
            f"{KEY_ENV_VAR} is malformed: expected a 32-byte url-safe base64 Fernet key (44 characters ending in '='). {KEY_GENERATE_HINT}",
        ) from error


def key_configured() -> bool:
    """Whether a usable key is present, so the UI can say why a form is disabled before it is filled."""
    try:
        _fernet()
    except CredentialCryptoError:
        return False
    return True


def encrypt_secret(secret: Dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(secret, sort_keys=True, separators=(",", ":")).encode()).decode()


def decrypt_secret(ciphertext: str) -> Dict[str, Any]:
    fernet = _fernet()
    try:
        secret = json.loads(fernet.decrypt(ciphertext.encode()).decode())
    except (InvalidToken, ValueError) as error:
        raise CredentialUndecryptableError(
            f"The stored credential can't be decrypted: {KEY_ENV_VAR} has changed since it was saved. Re-enter the credential for this account.",
        ) from error
    if not isinstance(secret, dict):
        raise CredentialUndecryptableError("The stored credential is unreadable. Re-enter the credential for this account.")
    return secret
