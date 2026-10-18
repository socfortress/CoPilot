"""The password policy: one definition for every password a user chooses (#1265).

Creating a user, an admin's reset and the self-service change (analyst frontend and
Customer Portal) all validate through ``validate_password``. Each frontend carries a
copy of the same rules in ``src/utils/password-policy.ts``, checked against the same
cases (``tests/fixtures/password_policy_cases.json``), so a form never accepts a
password the API refuses, or the other way round.

The rules, in the order they are checked (the first that fails is the one reported):

- no control, format or lone-surrogate character (Unicode Cc, Cf, Cs): a NUL byte is
  refused by bcrypt, and an invisible character is one nobody can type again;
- at least 8 characters (code points);
- at most 72 bytes of UTF-8, bcrypt's input limit (``AuthHandler._to_bcrypt_bytes``
  would otherwise drop the rest silently): an accented letter takes 2, an emoji 4;
- a lowercase letter (Ll), an uppercase letter (Lu), a digit (Nd);
- a symbol: any punctuation or symbol character (P*, S*), e.g. ``! @ # $ % _ - . + ^ €``.

Any other character is allowed: spaces, accented letters, symbols of any script. The
policy only ever applies to a new password; logging in never checks it, so a password
set under an older rule keeps working.

Failures are ``ValueError``: inside a Pydantic validator that becomes the standard 422
naming the field. Nothing here depends on FastAPI or the database.
"""
import unicodedata
from typing import Optional

MIN_PASSWORD_CHARACTERS = 8
MAX_PASSWORD_BYTES = 72

PASSWORD_REQUIREMENTS = "8 to 72 characters, with an uppercase letter, a lowercase letter, a digit and a symbol"

PASSWORD_PROBLEMS = {
    "control_character": "Password must not contain control or invisible characters",
    "too_short": "Password must be at least 8 characters long",
    "too_long": "Password must be at most 72 bytes long (an accented letter takes 2, an emoji 4)",
    "no_lowercase": "Password must contain a lowercase letter",
    "no_uppercase": "Password must contain an uppercase letter",
    "no_digit": "Password must contain a digit",
    "no_symbol": "Password must contain a symbol, such as ! @ # $ % _ - . or +",
}

_REFUSED_CATEGORIES = {"Cc", "Cf", "Cs"}


def password_problem_code(password: str) -> Optional[str]:
    """The key in ``PASSWORD_PROBLEMS`` of the first rule the password breaks, or None."""
    categories = [unicodedata.category(character) for character in password]
    if any(category in _REFUSED_CATEGORIES for category in categories):
        return "control_character"
    if len(password) < MIN_PASSWORD_CHARACTERS:
        return "too_short"
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "too_long"
    if "Ll" not in categories:
        return "no_lowercase"
    if "Lu" not in categories:
        return "no_uppercase"
    if "Nd" not in categories:
        return "no_digit"
    if not any(category[0] in "PS" for category in categories):
        return "no_symbol"
    return None


def validate_password(password: str) -> str:
    """The password unchanged, or ``ValueError`` naming the first rule it breaks."""
    code = password_problem_code(password)
    if code is not None:
        raise ValueError(PASSWORD_PROBLEMS[code])
    return password
