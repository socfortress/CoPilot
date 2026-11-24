import type {
	CloudAccount,
	CloudCheck,
	CloudComplianceFramework,
	CloudFinding,
	CloudRequirement,
	CloudScan,
	CloudScanCounts
} from "@/types/cloud-assessment"

export function counts(overrides: Partial<CloudScanCounts> = {}): CloudScanCounts {
	return {
		total: 0,
		passed: 0,
		failed: 0,
		manual: 0,
		muted: 0,
		failed_critical: 0,
		failed_high: 0,
		failed_medium: 0,
		failed_low: 0,
		failed_informational: 0,
		failed_unknown: 0,
		new_failed: 0,
		resolved_failed: 0,
		...overrides
	}
}

/** A completed scan's counts: 445 results, 61 failing. */
export const SCAN_COUNTS = counts({
	total: 445,
	passed: 380,
	failed: 61,
	manual: 4,
	failed_critical: 3,
	failed_high: 20,
	failed_medium: 30,
	failed_low: 8,
	new_failed: 5,
	resolved_failed: 2
})

export function account(overrides: Partial<CloudAccount> = {}): CloudAccount {
	return {
		id: 1,
		customer_code: "ACME",
		name: "Production",
		provider: "aws",
		auth_method: "role",
		config: { role_arn: "arn:aws:iam::123456789012:role/ProwlerScan" },
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
		last_connection_test_at: "2026-11-20T09:00:00",
		last_connection_ok: true,
		last_connection_error: null,
		last_connection_message: null,
		created_by: "admin",
		created_at: "2026-11-01T09:00:00",
		updated_by: null,
		updated_at: null,
		last_scan: null,
		last_completed_scan: null,
		...overrides
	}
}

export function scan(id: number, overrides: Partial<CloudScan> = {}): CloudScan {
	return {
		id,
		account_id: 1,
		account_name: "Production",
		provider: "aws",
		customer_code: "ACME",
		status: "completed",
		trigger_type: "manual",
		requested_by: "admin",
		queued_at: "2026-11-20T10:00:00",
		started_at: "2026-11-20T10:00:05",
		completed_at: "2026-11-20T10:20:00",
		duration_seconds: 1195,
		prowler_version: "5.13.1",
		counts: SCAN_COUNTS,
		check_errors: 0,
		error_code: null,
		error_message: null,
		prowler_errors: [],
		reports: ["html", "csv"],
		findings_pruned: false,
		previous_scan_id: id > 1 ? id - 1 : null,
		...overrides
	}
}

export function check(checkId: string, overrides: Partial<CloudCheck> = {}): CloudCheck {
	return {
		check_id: checkId,
		title: `Title of ${checkId}`,
		service: checkId.split("_")[0] ?? "",
		severity: "high",
		description: null,
		risk: null,
		remediation: null,
		remediation_urls: [],
		additional_urls: [],
		categories: [],
		compliance: {},
		passed: 1,
		failed: 2,
		manual: 0,
		muted: 0,
		status: "fail",
		...overrides
	}
}

export function finding(id: number, overrides: Partial<CloudFinding> = {}): CloudFinding {
	return {
		id,
		finding_uid: `prowler-aws-s3_bucket_public_access-123456789012-eu-west-1-bucket-${id}`,
		check_id: "s3_bucket_public_access",
		check_title: "Ensure S3 buckets are not publicly accessible",
		status: "FAIL",
		severity: "critical",
		muted: false,
		status_extended: `Bucket bucket-${id} is public.`,
		service: "s3",
		region: "eu-west-1",
		cloud_account_uid: "123456789012",
		cloud_account_name: "acme-prod",
		resource_uid: `arn:aws:s3:::bucket-${id}`,
		resource_name: `bucket-${id}`,
		resource_type: "AwsS3Bucket",
		resource_tags: [],
		detected_at: "2026-11-20T10:10:00",
		first_seen_at: "2026-11-20T10:10:00",
		is_new: true,
		...overrides
	}
}

export function framework(key: string, overrides: Partial<CloudComplianceFramework> = {}): CloudComplianceFramework {
	return {
		key,
		framework: key,
		version: null,
		name: `${key} framework`,
		description: null,
		requirements_total: 10,
		passed: 6,
		failed: 2,
		manual: 1,
		not_assessed: 1,
		...overrides
	}
}

export function requirement(id: string, overrides: Partial<CloudRequirement> = {}): CloudRequirement {
	return {
		id,
		name: `Requirement ${id}`,
		description: null,
		section: null,
		status: "pass",
		checks: [],
		...overrides
	}
}
