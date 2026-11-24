"""Write tests/fixtures/aws_sample.ocsf.json with Prowler's own OCSF writer (Prowler 5.52.0).

The runner's tests parse this file, so its layout (one JSON array, findings
pretty-printed and separated by commas, ``status`` "Suppressed" for muted
findings, raw resource configuration under ``resources[].data``) is exactly
what ``prowler <provider> -M json-ocsf`` writes.

Needs Prowler installed (``pip install prowler==<version>``); the runner's
tests themselves don't. Usage:

    python make_ocsf_fixture.py <output.ocsf.json>
"""

import sys
from datetime import datetime
from datetime import timezone

from prowler.lib.check.models import CheckMetadata
from prowler.lib.check.models import Code
from prowler.lib.check.models import Recommendation
from prowler.lib.check.models import Remediation
from prowler.lib.outputs.finding import Finding
from prowler.lib.outputs.ocsf.ocsf import OCSF

TIMESTAMP = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)
ACCOUNT = "123456789012"


def finding(
    *,
    uid,
    check_id,
    title,
    service,
    severity,
    status,
    status_extended,
    resource_uid,
    resource_name,
    region="eu-west-1",
    muted=False,
    resource_tags=None,
    resource_metadata=None,
    compliance=None,
    remediation_url=None,
):
    return Finding(
        auth_method="assumed_role",
        timestamp=TIMESTAMP,
        account_uid=ACCOUNT,
        account_name="production",
        account_email="",
        account_organization_uid="o-exampleorg",
        account_organization_name="Example Org",
        account_tags={"cost-center": "security"},
        uid=uid,
        status=status,
        status_extended=status_extended,
        muted=muted,
        resource_uid=resource_uid,
        resource_name=resource_name,
        resource_details="",
        resource_metadata=resource_metadata or {},
        resource_tags=resource_tags or {},
        partition="aws",
        region=region,
        compliance=compliance or {},
        metadata=CheckMetadata(
            Provider="aws",
            CheckID=check_id,
            CheckTitle=title,
            CheckType=["Software and Configuration Checks/AWS Security Best Practices"],
            ResourceType="AwsEcsTaskDefinition",
            ServiceName=service,
            SubServiceName="",
            ResourceIdTemplate="",
            Severity=severity,
            Description=f"Description of {check_id}.",
            Risk=f"Risk of {check_id}.",
            RelatedUrl="",  # deprecated: Prowler requires it empty
            Remediation=Remediation(
                Recommendation=Recommendation(
                    Text=f"Fix {check_id}.",
                    Url=remediation_url if remediation_url is not None else f"https://hub.prowler.com/check/{check_id}",
                ),
                Code=Code(NativeIaC="", Terraform="", Other="", CLI=""),
            ),
            DependsOn=[],
            RelatedTo=[],
            Categories=["secrets"] if service == "ecs" else ["identity-access"],
            Notes="",
            AdditionalURLs=["https://example.com/additional"],
        ),
    )


FINDINGS = [
    finding(
        uid="prowler-aws-ecs_task_definitions_no_environment_secrets-123456789012-eu-west-1-api:7",
        check_id="ecs_task_definitions_no_environment_secrets",
        title="ECS task definitions have no secrets in environment variables",
        service="ecs",
        severity="critical",
        status="FAIL",
        status_extended="Potential secrets found in ECS task definition api with revision 7: Secret Keyword on the environment variable DB_PASSWORD.",
        resource_uid="arn:aws:ecs:eu-west-1:123456789012:task-definition/api:7",
        resource_name="api:7",
        resource_tags={"env": "prod", "owner": "team-a"},
        # Raw resource configuration: the runner must never pass this on.
        resource_metadata={"environment": [{"name": "DB_PASSWORD", "value": "FIXTURE-SECRET-VALUE"}]},
        compliance={"MITRE-ATTACK": ["T1552"], "CIS-5.0": ["5.1"]},
    ),
    finding(
        uid="prowler-aws-ecs_task_definitions_no_environment_secrets-123456789012-eu-west-1-web:3",
        check_id="ecs_task_definitions_no_environment_secrets",
        title="ECS task definitions have no secrets in environment variables",
        service="ecs",
        severity="critical",
        status="PASS",
        status_extended="No secrets found in ECS task definition web with revision 3.",
        resource_uid="arn:aws:ecs:eu-west-1:123456789012:task-definition/web:3",
        resource_name="web:3",
        compliance={"MITRE-ATTACK": ["T1552"], "CIS-5.0": ["5.1"]},
    ),
    finding(
        uid="prowler-aws-s3_bucket_public_access-123456789012-us-east-1-logs-bucket",
        check_id="s3_bucket_public_access",
        title="S3 bucket is not publicly accessible",
        service="s3",
        severity="medium",
        status="FAIL",
        status_extended="S3 Bucket logs-bucket is publicly accessible.",
        resource_uid="arn:aws:s3:::logs-bucket",
        resource_name="logs-bucket",
        region="us-east-1",
        muted=True,
        compliance={"CIS-5.0": ["2.1.4"]},
    ),
    finding(
        uid="prowler-aws-account_maintain_current_contact_details-123456789012-us-east-1-123456789012",
        check_id="account_maintain_current_contact_details",
        title="Maintain current contact details",
        service="account",
        severity="low",
        status="MANUAL",
        status_extended="Login to the AWS Console. Choose your account name on the top right of the window and check the contact information.",
        resource_uid="arn:aws:iam::123456789012:root",
        resource_name="123456789012",
        region="us-east-1",
        compliance={"CIS-5.0": ["1.1"]},
    ),
    finding(
        uid="prowler-aws-iam_root_mfa_enabled-123456789012-us-east-1-root",
        check_id="iam_root_mfa_enabled",
        title="Root account has MFA enabled",
        service="iam",
        severity="high",
        # Hidden characters arrive in names and tags from the customer's cloud.
        status="FAIL",
        status_extended="MFA is not enabled for root account.\u0007",
        resource_uid="arn:aws:iam::123456789012:root",
        resource_name="root\u202e",
        region="us-east-1",
        compliance={"CIS-5.0": ["1.5"], "MITRE-ATTACK": ["T1078"]},
    ),
    finding(
        uid="prowler-aws-cloudtrail_multi_region_enabled-123456789012-us-east-1-123456789012",
        check_id="cloudtrail_multi_region_enabled",
        title="CloudTrail trail is enabled in all regions",
        service="cloudtrail",
        severity="informational",
        status="PASS",
        status_extended="Trail org-trail is multiregion and it is logging.",
        resource_uid="arn:aws:cloudtrail:us-east-1:123456789012:trail/org-trail",
        resource_name="org-trail",
        region="us-east-1",
        compliance={"CIS-5.0": ["3.1"]},
    ),
    finding(
        uid="prowler-aws-ec2_instance_public_ip-123456789012-eu-west-1-i-0abc",
        check_id="ec2_instance_public_ip",
        title="EC2 instance does not have a public IP address",
        service="ec2",
        severity="medium",
        status="FAIL",
        status_extended="EC2 Instance i-0abc has a public IP address. " + "x" * 3000,
        resource_uid="arn:aws:ec2:eu-west-1:123456789012:instance/i-0abc",
        resource_name="i-0abc",
        compliance={},
    ),
]


def main(path: str) -> None:
    output = OCSF(findings=FINDINGS, file_path=path)
    output.batch_write_data_to_file()


if __name__ == "__main__":
    main(sys.argv[1])
