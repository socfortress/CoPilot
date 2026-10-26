"""The Customer Portal's languages (#1310): which exist, and the rule that English always does.

Pure, so the request schemas, the service and the tests share one definition. The portal's own
list (``customer-portal/src/lang/config.ts``) and CoPilot's (``frontend/src/components/
customerPortal/portalLanguages.ts``) must name the same codes.
"""

from typing import Iterable
from typing import List

#: Every language the portal ships, in the order the pickers list them; English first.
SUPPORTED_LOCALES = ("en", "it", "de", "fr", "es", "nl", "cs")

#: Always enabled, the default, and what the portal falls back to.
DEFAULT_LOCALE = "en"


def ordered(codes: Iterable[str]) -> List[str]:
    """The supported codes among ``codes``, once each, in ``SUPPORTED_LOCALES`` order, English first."""
    wanted = set(codes) | {DEFAULT_LOCALE}
    return [code for code in SUPPORTED_LOCALES if code in wanted]


def check_languages(codes: List[str]) -> List[str]:
    """A customer's languages as an admin sent them: English among them, every code known.

    Raises ``ValueError`` (a 422 naming the field) rather than repairing the list: an admin who
    sent ``["it"]`` should learn that English stays, not find it quietly added.
    """
    unknown = sorted({code for code in codes if code not in SUPPORTED_LOCALES})
    if unknown:
        raise ValueError(f"Unknown language: {', '.join(unknown)}. Supported: {', '.join(SUPPORTED_LOCALES)}")
    if DEFAULT_LOCALE not in codes:
        raise ValueError("English is always enabled and cannot be removed")
    return ordered(codes)


def effective_locale(picked: str | None, available: Iterable[str]) -> str:
    """The language the portal shows: the user's pick while it is enabled for them, else English."""
    return picked if picked and picked in set(available) else DEFAULT_LOCALE
