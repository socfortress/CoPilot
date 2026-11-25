"""The report's ``config``: which SOCFortress default release the customer's stored Sysmon config is, unmodified.

Self-reported from what CoPilot deploys (the customer's stored config, sysmon-configs/<code>/sysmon_config.xml), not
from each endpoint: a release sequence when the stored config, its install folder turned back into the installer's
placeholder, is that release's content (line endings aside); ``"customized"`` when it is none of the releases this
CoPilot knows; ``"unknown"`` when there is no stored config or no known release.
"""
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Tuple
from typing import Union

from app.active_response.services.sysmon_config import templatize_install_dir
from app.active_response.services.sysmon_default_sync import same_config

# sequence -> (content_sha256, content_sha256_crlf)
Releases = Dict[int, Tuple[str, Optional[str]]]


def config_value(stored: Optional[bytes], releases: Releases, install_dirs: Iterable[str]) -> Union[int, str]:
    if stored is None or not releases:
        return "unknown"
    try:
        text = stored.decode("utf-8")
    except UnicodeDecodeError:
        return "unknown"
    candidates = [None] + [d for d in install_dirs if d]
    for install_dir in candidates:
        templ, _ = templatize_install_dir(text, install_dir) if install_dir else (text, 0)
        data = templ.encode("utf-8")
        for sequence in sorted(releases, reverse=True):
            sha, sha_crlf = releases[sequence]
            if same_config(data, sha, sha_crlf):
                return sequence
    return "customized"
