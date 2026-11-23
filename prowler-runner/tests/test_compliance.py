"""The framework catalog, keyed as Prowler keys a finding's compliance mapping."""

import json
import shutil

from runner.compliance import build_catalog
from runner.compliance import framework_key
from tests.support import FIXTURES


def test_keys_match_the_findings():
    assert framework_key("CIS", "5.0") == "CIS-5.0"
    assert framework_key("MITRE-ATTACK", "") == "MITRE-ATTACK"
    assert framework_key("KISA-ISMS-P", "2023-korean") == "KISA-ISMS-P-2023-korean"


def test_catalog(tmp_path):
    shutil.copytree(FIXTURES / "compliance", tmp_path / "compliance")
    aws = tmp_path / "compliance" / "aws"
    (aws / "broken.json").write_text("{not json")
    (aws / "misplaced_azure.json").write_text(json.dumps({"Framework": "CIS", "Version": "4.0", "Provider": "Azure", "Requirements": []}))

    catalog = build_catalog(tmp_path / "compliance", "aws", "5.52.0")
    assert catalog["prowler_version"] == "5.52.0"
    assert catalog["skipped_files"] == 2
    frameworks = {framework["key"]: framework for framework in catalog["frameworks"]}
    assert list(frameworks) == ["CIS-5.0", "MITRE-ATTACK"]
    cis = frameworks["CIS-5.0"]
    assert cis["file"] == "cis_5.0_aws"
    assert [requirement["id"] for requirement in cis["requirements"]] == ["1.1", "1.5", "2.1.4", "4.1"]
    mfa = cis["requirements"][1]
    assert mfa["section"] == "1 Identity and Access Management"
    assert mfa["checks"] == ["iam_root_mfa_enabled"]  # the malformed check name is dropped
    assert cis["requirements"][3]["checks"] == []  # a manual requirement
    assert frameworks["MITRE-ATTACK"]["requirements"][0]["name"] == "Unsecured Credentials"


def test_a_provider_without_files_has_no_frameworks(tmp_path):
    assert build_catalog(tmp_path, "gcp", None)["frameworks"] == []


def test_the_catalog_route(client):
    first = client.get("/v1/compliance/aws")
    assert first.status_code == 200
    assert [framework["key"] for framework in first.json()["frameworks"]] == ["CIS-5.0", "MITRE-ATTACK"]
    assert client.get("/v1/compliance/aws").content == first.content
    unknown = client.get("/v1/compliance/kubernetes")
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "unknown_provider"
