"""A customer's business profile as the SOC records it (talon-analyst plan K1-8): when and where it works.

talon-analyst turns an event's time into the customer's local time and says whether it falls inside
these hours, and says whether a geolocated address is in a country the customer operates in. A wrong
time zone puts every alert at the wrong hour, so these checks keep the entries exact:

- **A time zone** is an IANA name (``America/Denver``), never an abbreviation (``MST``, ``EST5EDT``):
  those are ambiguous, and most ignore daylight saving. ``UTC`` is the one name without a region.
  The ``Etc/GMT±N`` zones are refused too: their sign is the reverse of the offset they name.
- **The working week** has an SLA business-hours calendar's shape and rules (``soc_management``), so
  one can be copied into the other: per day, windows of ``HH:MM`` in that zone that start before they
  end and don't overlap. A closed day is left out, and a night shift is two windows on two days. A
  customer that works around the clock says so (``always_open``), with no windows. A profile may give
  neither: talon-analyst then shows the local time only.
- **Countries** are ISO 3166-1 alpha-2 codes, the form log pipelines geolocate addresses to.

Every refusal is a fixed text that never echoes input.
"""

import re
from functools import lru_cache
from typing import Any
from typing import Dict
from typing import FrozenSet
from typing import List
from typing import Mapping
from typing import Sequence
from zoneinfo import available_timezones

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

BAD_TIME_ZONE = "pick a time zone by its region and city, such as America/Denver"
BAD_HOUR = "enter times as HH:MM, from 00:00 to 23:59"
BACKWARDS = "a window must start before it ends: record a night shift as two windows on two days"
OVERLAP = "windows of one day must not overlap"
OPEN_WITH_HOURS = "a customer open around the clock has no business hours to record: clear them, or the switch"
BAD_COUNTRY = "enter countries as two-letter ISO codes, such as US or GB"

_HHMM = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")

# fmt: off
#: ISO 3166-1 alpha-2, as the IANA time zone database lists them (``iso3166.tab``), and ``XK``
#: (Kosovo): not assigned by ISO, but what geolocation databases use.
COUNTRIES: FrozenSet[str] = frozenset(
    """
    AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS
    BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE
    EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM
    HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC
    LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA
    NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW
    SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO
    TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW
    XK
    """.split(),
)
# fmt: on


class BusinessProblem(ValueError):
    """A business profile that can't be saved. Its text is one of the fixed texts above."""


@lru_cache(maxsize=1)
def _zones() -> Dict[str, str]:
    """The zones a profile may name, by their lower-case name. From the system's time zone database
    (the image installs ``tzdata``), read once."""
    usable = {
        name
        for name in available_timezones()
        if name == "UTC" or ("/" in name and not name.startswith(("Etc/", "SystemV/", "posix/", "right/")))
    }
    return {name.lower(): name for name in usable}


def checked_time_zone(value: Any) -> str:
    """The zone's own name, whatever its case (``america/denver`` is ``America/Denver``)."""
    name = _zones().get(str(value).strip().lower())
    if name is None:
        raise BusinessProblem(BAD_TIME_ZONE)
    return name


def _hour(value: Any) -> str:
    text = str(value).strip()
    if not _HHMM.fullmatch(text):
        raise BusinessProblem(BAD_HOUR)
    return text


def checked_week(week: Mapping[str, Sequence[Sequence[Any]]], always_open: bool) -> Dict[str, List[List[str]]]:
    """The open days in week order, each with its windows in order."""
    kept: Dict[str, List[List[str]]] = {}
    for day in WEEKDAYS:
        windows = sorted([_hour(start), _hour(end)] for start, end in week.get(day) or ())
        if any(start >= end for start, end in windows):
            raise BusinessProblem(BACKWARDS)
        if any(later[0] < earlier[1] for earlier, later in zip(windows, windows[1:])):
            raise BusinessProblem(OVERLAP)
        if windows:
            kept[day] = windows
    if always_open and kept:
        raise BusinessProblem(OPEN_WITH_HOURS)
    return kept


def checked_countries(values: Sequence[Any]) -> List[str]:
    """Upper case, each once, in order."""
    codes = {str(value).strip().upper() for value in values}
    if not codes <= COUNTRIES:
        raise BusinessProblem(BAD_COUNTRY)
    return sorted(codes)
