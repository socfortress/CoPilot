"""Branding / theming for the customer Incident-Management PDF report.

A report can be rendered with one of two brand themes (see ``BrandTheme`` in
``app.incidents.schema.customer_report``):

- ``"socfortress"`` — the SOCFortress logo + the SOCFortress brand colour
  (``#fc862e``, the orange of the wordmark).
- ``"customer"`` — the customer portal logo/title (from ``customer_portal_settings``)
  and the customer *brand color*. The brand color is taken from the new
  ``customer_portal_settings.brand_color`` field; when it is unset we fall back to
  the dominant color derived from the portal logo (via Pillow), and if that also
  fails (e.g. an SVG logo Pillow cannot rasterise, or no logo at all) we fall back
  to the SOCFortress orange so the report always renders.

Both themes build their full palette from a single *base* brand colour via
``_build_palette``. The color values are injected as *literal* hex strings into
the Jinja template's ``<style>`` block — wkhtmltopdf runs an old WebKit that does
not support CSS ``var()``, so custom properties are not an option.

Contrast is handled explicitly so text is always legible regardless of the brand
colour: ``accent`` (colored text on the white page) is darkened until it clears a
minimum contrast ratio against white, and ``accent_text`` (text drawn on the
``accent_strong`` fill) is whichever of dark-slate / white contrasts better.
"""
import base64
import binascii
import io
import os
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.universal_models import CustomerPortalSettings

# --- SOCFortress brand constants ---------------------------------------------
SOCF_BASE = "#fc862e"  # the orange of the SOCFortress wordmark
SOCF_TITLE = "SOCFortress"
SOCF_FOOTER_BRAND = "SOCFortress"

# Text colours used on filled backgrounds (picked by contrast, never both).
_DARK_TEXT = "#0f172a"  # slate-900
_WHITE_TEXT = "#ffffff"
# Minimum contrast ratio for coloured text on the white page (WCAG AA large text
# is 3:1; we aim a little higher so normal-weight labels stay comfortable).
_MIN_TEXT_ON_WHITE = 3.5

_LOGO_ASSET = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "assets", "socfortress_logo.svg")

_socfortress_logo_cache: Optional[str] = None


def _load_socfortress_logo() -> Optional[str]:
    """Return the SOCFortress logo as an ``image/svg+xml`` base64 data URI (cached)."""
    global _socfortress_logo_cache
    if _socfortress_logo_cache is not None:
        return _socfortress_logo_cache or None
    try:
        with open(_LOGO_ASSET, "rb") as fh:
            data = fh.read()
        _socfortress_logo_cache = f"data:image/svg+xml;base64,{base64.b64encode(data).decode('ascii')}"
    except OSError as exc:
        logger.warning(f"Could not load SOCFortress report logo from {_LOGO_ASSET}: {exc}")
        _socfortress_logo_cache = ""  # sentinel: tried and failed, don't retry
    return _socfortress_logo_cache or None


# --- Colour helpers ----------------------------------------------------------
def _hex_to_rgb(value: str) -> Optional[Tuple[int, int, int]]:
    """Parse ``#RGB`` / ``#RRGGBB`` into an ``(r, g, b)`` tuple, or None if invalid."""
    if not value:
        return None
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6:
        return None
    try:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    except ValueError:
        return None


def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _normalize_hex(value: Optional[str]) -> Optional[str]:
    rgb = _hex_to_rgb(value) if value else None
    return _rgb_to_hex(rgb) if rgb else None


def _lighten(value: str, amount: float) -> str:
    """Mix ``value`` toward white by ``amount`` (0..1)."""
    rgb = _hex_to_rgb(value) or (0, 0, 0)
    return _rgb_to_hex(tuple(c + (255 - c) * amount for c in rgb))


def _darken(value: str, amount: float) -> str:
    """Mix ``value`` toward black by ``amount`` (0..1)."""
    rgb = _hex_to_rgb(value) or (0, 0, 0)
    return _rgb_to_hex(tuple(c * (1 - amount) for c in rgb))


def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """WCAG relative luminance of an sRGB colour (0..1)."""

    def _lin(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """WCAG contrast ratio between two colours (1..21)."""
    lum1 = _relative_luminance(rgb1)
    lum2 = _relative_luminance(rgb2)
    hi, lo = max(lum1, lum2), min(lum1, lum2)
    return (hi + 0.05) / (lo + 0.05)


def _contrast_text(value: str) -> str:
    """Return whichever of dark-slate / white text is more legible on ``value``."""
    rgb = _hex_to_rgb(value) or (0, 0, 0)
    dark = _hex_to_rgb(_DARK_TEXT)
    white = (255, 255, 255)
    return _DARK_TEXT if _contrast_ratio(rgb, dark) >= _contrast_ratio(rgb, white) else _WHITE_TEXT


def _readable_on_white(value: str, min_ratio: float = _MIN_TEXT_ON_WHITE) -> str:
    """Darken ``value`` until it clears ``min_ratio`` contrast against a white page.

    Returns the colour unchanged when it is already dark enough; falls back to
    dark slate if even near-black cannot reach the target (it always can).
    """
    white = (255, 255, 255)
    base = _hex_to_rgb(value)
    if not base:
        return _DARK_TEXT
    if _contrast_ratio(base, white) >= min_ratio:
        return _rgb_to_hex(base)
    for step in range(1, 21):
        candidate = _darken(value, step * 0.05)
        rgb = _hex_to_rgb(candidate)
        if rgb and _contrast_ratio(rgb, white) >= min_ratio:
            return candidate
    return _DARK_TEXT


def _derive_color_from_logo(logo_base64: Optional[str], mime_type: Optional[str]) -> Optional[str]:
    """Extract a representative dominant colour from a raster logo via Pillow.

    Returns ``None`` on any failure (e.g. SVG logos Pillow cannot rasterise, or an
    undecodable payload). Near-white and near-black pixels are ignored so the
    result is an actual brand hue rather than the background/outline.
    """
    if not logo_base64:
        return None
    if mime_type and "svg" in mime_type.lower():
        return None  # Pillow cannot rasterise SVG

    payload = logo_base64
    if payload.startswith("data:"):
        payload = payload.split(",", 1)[1] if "," in payload else ""
    try:
        raw = base64.b64decode(payload)
    except (binascii.Error, ValueError):
        return None

    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow is a hard dependency
        return None

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        # Flatten onto white so transparent regions read as background.
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img).convert("RGB")
        img.thumbnail((80, 80))
        # Quantize to a small palette and pick the most common non-neutral colour.
        quantized = img.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
        palette = quantized.getpalette() or []
        counts = quantized.getcolors() or []  # list of (count, palette_index)
        counts.sort(reverse=True)
        best: Optional[str] = None
        for _count, idx in counts:
            r, g, b = palette[idx * 3 : idx * 3 + 3]
            # Skip near-white and near-black (background / outlines).
            if max(r, g, b) > 235 and min(r, g, b) > 235:
                continue
            if max(r, g, b) < 30:
                continue
            best = _rgb_to_hex((r, g, b))
            break
        return best
    except Exception as exc:  # noqa: BLE001 - defensive: any decode/quantize failure -> fallback
        logger.debug(f"Could not derive brand color from logo: {exc}")
        return None


def _customer_logo_data_uri(settings: Optional[CustomerPortalSettings]) -> Optional[str]:
    if not settings or not settings.logo_base64:
        return None
    if settings.logo_base64.startswith("data:"):
        return settings.logo_base64
    mime = settings.logo_mime_type or "image/png"
    return f"data:{mime};base64,{settings.logo_base64}"


def _build_palette(base: Optional[str], logo: Optional[str], title: str, footer_brand: str) -> Dict[str, Any]:
    """Build a full report theme from a single base brand colour.

    All contrast-sensitive values are derived from ``base`` so any brand colour —
    light or dark — stays legible:
      * ``accent`` — coloured text on the white page (darkened to clear contrast).
      * ``accent_strong`` — a filled header/band background (the raw brand colour).
      * ``accent_text`` — text on that fill (dark-slate or white, whichever reads).
      * ``accent_soft`` — a light tint used for subtle borders.
    """
    base = _normalize_hex(base) or SOCF_BASE
    return {
        "logo": logo,
        "title": title,
        "footer_brand": footer_brand,
        "accent": _readable_on_white(base),
        "accent_strong": base,
        "accent_text": _contrast_text(base),
        "accent_soft": _lighten(base, 0.82),
        # Mono-colour charts follow the brand; two evolution shades stay distinct.
        "chart_bar": base,
        "chart_evo_alerts": base,
        "chart_evo_cases": _darken(base, 0.22),
    }


def _socfortress_theme() -> Dict[str, Any]:
    return _build_palette(SOCF_BASE, _load_socfortress_logo(), SOCF_TITLE, SOCF_FOOTER_BRAND)


def _customer_theme(settings: Optional[CustomerPortalSettings]) -> Dict[str, Any]:
    title = (settings.title if settings and settings.title else None) or "CoPilot"
    logo = _customer_logo_data_uri(settings)

    # Brand color: explicit setting first, then dominant colour of the logo, then
    # the SOCFortress orange as a last resort so the report always renders.
    base = _normalize_hex(settings.brand_color if settings else None)
    if not base:
        base = _derive_color_from_logo(
            settings.logo_base64 if settings else None,
            settings.logo_mime_type if settings else None,
        )
    if not base:
        base = SOCF_BASE
    return _build_palette(base, logo, title, title)


async def resolve_theme(session: AsyncSession, brand_theme: str) -> Dict[str, Any]:
    """Resolve the branding dict for a report given the requested ``brand_theme``.

    Always returns a fully-populated theme (falls back to the SOCFortress orange
    for any missing colour) so the template can render unconditionally.
    """
    if brand_theme == "socfortress":
        return _socfortress_theme()

    result = await session.execute(select(CustomerPortalSettings).limit(1))
    settings = result.scalars().first()
    return _customer_theme(settings)
