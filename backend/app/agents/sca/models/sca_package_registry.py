"""
Registry that maps SCA application categories to the package names you would
expect to find on agents via the Wazuh Indexer.

To add support for a new application:
  1. Add a new entry to ``SCA_PACKAGE_REGISTRY`` below.
  2. Set ``sca_application`` to the value used in the CoPilot-SCA index.json
     ``application`` field so the link back to available policies is automatic.
  3. List every package name pattern (lowercase) that indicates the software
     is installed.  These are matched with an OpenSearch **wildcard** query
     (``*pattern*``), so partial names work.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List


@dataclass(frozen=True)
class ScaPackageEntry:
    """A single entry in the SCA package registry."""

    # Human-readable label shown in API responses.
    display_name: str

    # The ``application`` value from the CoPilot-SCA index.json so we can
    # cross-reference available policies automatically.
    sca_application: str

    # Package-name patterns to search for in the Wazuh Indexer.  Each
    # pattern is matched case-insensitively with wildcards on both sides.
    package_patterns: List[str] = field(default_factory=list)


# ── The registry ────────────────────────────────────────────────────────
# Add new entries here as SCA policies are created for more applications.

SCA_PACKAGE_REGISTRY: Dict[str, ScaPackageEntry] = {
    "apache": ScaPackageEntry(
        display_name="Apache HTTP Server",
        sca_application="apache",
        package_patterns=["apache2", "httpd", "apache2-bin", "apache2-utils"],
    ),
    "nginx": ScaPackageEntry(
        display_name="NGINX",
        sca_application="nginx",
        package_patterns=["nginx", "nginx-common", "nginx-core", "nginx-full"],
    ),
    "iis": ScaPackageEntry(
        display_name="Microsoft IIS",
        sca_application="iis",
        package_patterns=["iis", "w3svc"],
    ),
    "mysql": ScaPackageEntry(
        display_name="MySQL / MariaDB",
        sca_application="mysql",
        package_patterns=[
            "mysql-server",
            "mysql-community-server",
            "mysql-common",
            "mariadb-server",
            "mariadb-common",
        ],
    ),
    "postgresql": ScaPackageEntry(
        display_name="PostgreSQL",
        sca_application="postgresql",
        package_patterns=["postgresql", "postgresql-common", "postgresql-client"],
    ),
    "sqlserver": ScaPackageEntry(
        display_name="Microsoft SQL Server",
        sca_application="sqlserver",
        package_patterns=["mssql-server", "mssql-tools"],
    ),
}
