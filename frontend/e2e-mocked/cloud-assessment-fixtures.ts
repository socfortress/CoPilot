import type {
	CloudAccount,
	CloudAccountScanBrief,
	CloudAvailability,
	CloudCheck,
	CloudComplianceFramework,
	CloudFinding,
	CloudRequirement,
	CloudScan,
	CloudScanCounts
} from "../src/types/cloud-assessment"

/** One customer's AWS account with three scans, for the Cloud Security Assessment page (#1328). */

export const CUSTOMER = "ACME"
export const ACCOUNT_ID = 1
export const LATEST = 11

/** Text the customer's cloud sent: shown as text, never run. */
export const HOSTILE_DETAIL = `<img src=x onerror="window.__cloudXss=1">Bucket logs is public.`

export const COUNTS: CloudScanCounts = {
	total: 445,
	passed: 380,
	failed: 61,
	manual: 4,
	muted: 2,
	failed_critical: 3,
	failed_high: 20,
	failed_medium: 30,
	failed_low: 8,
	failed_informational: 0,
	failed_unknown: 0,
	new_failed: 5,
	resolved_failed: 2
}

export const AVAILABILITY: CloudAvailability = {
	encryption_key_configured: true,
	runner_configured: true,
	runner_reachable: true,
	runner_problem: null,
	runner_version: "1.0.0",
	prowler_version: "5.52.0",
	powershell: true,
	providers: ["aws", "azure", "gcp", "m365"]
}

const brief: CloudAccountScanBrief = {
	id: LATEST,
	status: "completed",
	trigger_type: "schedule",
	queued_at: "2026-11-22T02:00:00",
	completed_at: "2026-11-22T02:19:00",
	counts: COUNTS,
	error_code: null,
	previous_scan_id: 10
}

export const ACCOUNT: CloudAccount = {
	id: ACCOUNT_ID,
	customer_code: CUSTOMER,
	name: "Production",
	provider: "aws",
	auth_method: "role",
	config: { role_arn: "arn:aws:iam::123456789012:role/ProwlerScan", regions: ["eu-west-1"] },
	cloud_account: "123456789012",
	external_id: "copilot-0123456789abcdef0123456789abcdef",
	secret_configured: true,
	secret_hint: "…MPLE",
	secret_expires_at: null,
	secret_expires_in_days: null,
	enabled: true,
	schedule: "daily",
	schedule_hour: 2,
	schedule_weekday: null,
	next_scheduled_at: "2026-11-24T02:00:00",
	last_connection_test_at: "2026-11-21T10:00:00",
	last_connection_ok: true,
	last_connection_error: null,
	last_connection_message: null,
	created_by: "admin",
	created_at: "2026-11-01T09:00:00",
	updated_by: null,
	updated_at: null,
	last_scan: brief,
	last_completed_scan: brief
}

function scan(id: number, previous: number | null, counts: CloudScanCounts = COUNTS): CloudScan {
	return {
		id,
		account_id: ACCOUNT_ID,
		account_name: "Production",
		provider: "aws",
		customer_code: CUSTOMER,
		status: "completed",
		trigger_type: "schedule",
		requested_by: null,
		queued_at: `2026-11-${id + 11}T02:00:00`,
		started_at: `2026-11-${id + 11}T02:00:30`,
		completed_at: `2026-11-${id + 11}T02:19:00`,
		duration_seconds: 1110,
		prowler_version: "5.52.0",
		counts,
		check_errors: 0,
		error_code: null,
		error_message: null,
		prowler_errors: [],
		reports: ["html", "csv"],
		findings_pruned: false,
		previous_scan_id: previous
	}
}

export const SCANS: CloudScan[] = [scan(11, 10), scan(10, 9), scan(9, null, { ...COUNTS, new_failed: 0, resolved_failed: 0 })]

export const CHECKS: CloudCheck[] = [
	{
		check_id: "ec2_instance_port_ssh_exposed_to_internet",
		title: "EC2 instance does not allow ingress from the Internet to TCP port 22",
		service: "ec2",
		severity: "critical",
		description: "**EC2 instances** whose security groups allow public **inbound TCP** access to port `22`.",
		risk: "Direct SSH exposure invites brute force.",
		remediation: "Restrict SSH to trusted sources only.",
		remediation_urls: ["javascript:alert(1)", "https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html"],
		additional_urls: [],
		categories: ["internet-exposed"],
		compliance: { "CIS-5.0": ["5.2"] },
		passed: 3,
		failed: 2,
		manual: 0,
		muted: 0,
		status: "fail"
	}
]

export const FINDINGS: CloudFinding[] = [
	{
		id: 501,
		finding_uid: "prowler-aws-ec2_instance_port_ssh_exposed_to_internet-123456789012-eu-west-1-i-0abc",
		check_id: "ec2_instance_port_ssh_exposed_to_internet",
		check_title: "EC2 instance does not allow ingress from the Internet to TCP port 22",
		status: "FAIL",
		severity: "critical",
		muted: false,
		status_extended: HOSTILE_DETAIL,
		service: "ec2",
		region: "eu-west-1",
		cloud_account_uid: "123456789012",
		cloud_account_name: "acme-production",
		resource_uid: "arn:aws:ec2:eu-west-1:123456789012:instance/i-0abc",
		resource_name: "i-0abc",
		resource_type: "AwsEc2Instance",
		resource_tags: ["env=prod"],
		detected_at: "2026-11-22T02:10:00",
		first_seen_at: "2026-11-22T02:10:00",
		is_new: true
	}
]

export const FRAMEWORK: CloudComplianceFramework = {
	key: "CIS-5.0",
	framework: "CIS",
	version: "5.0",
	name: "CIS Amazon Web Services Foundations Benchmark v5.0.0",
	description: null,
	requirements_total: 3,
	passed: 1,
	failed: 1,
	manual: 0,
	not_assessed: 1
}

/** Out of order on purpose, as some of Prowler's framework files list them: 1.10 before 1.2. */
export const REQUIREMENTS: CloudRequirement[] = [
	{ id: "1.10", name: "Ensure MFA is enabled for every console user", description: null, section: "1 IAM", status: "fail", checks: [] },
	{ id: "1.2", name: "Ensure security contact information is registered", description: null, section: "1 IAM", status: "not_assessed", checks: [] },
	{ id: "1.1", name: "Maintain current contact details", description: null, section: "1 IAM", status: "pass", checks: [] }
]
