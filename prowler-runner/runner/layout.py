"""Where a job's files live: ``<work dir>/<job id>/``.

- ``secrets/``: credential files (a GCP key), deleted as soon as Prowler exits
- ``out/``: what Prowler writes; its OCSF file and compliance CSVs are deleted once read
- ``summary.json``, ``findings.ndjson``: what the normalizer made of the OCSF file
"""

import re

JOB_ID = re.compile(r"^[0-9a-f]{32}$")
OUT_DIR = "out"
SECRETS_DIR = "secrets"
OUTPUT_NAME = "scan"
OCSF_FILE = f"{OUTPUT_NAME}.ocsf.json"
HTML_FILE = f"{OUTPUT_NAME}.html"
CSV_FILE = f"{OUTPUT_NAME}.csv"
COMPLIANCE_DIR = "compliance"
SUMMARY_FILE = "summary.json"
FINDINGS_FILE = "findings.ndjson"
