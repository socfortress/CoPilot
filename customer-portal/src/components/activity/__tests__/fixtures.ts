import type { Activity } from "@/types/activity"

/** A month of activity for ACME, the shape `GET /customer_portal/activity` answers (#1284). */
export function activityFixture(over: Partial<Activity> = {}): Activity {
	return {
		enabled: true,
		customer_codes: ["ACME"],
		range: "30d",
		since: "2026-09-01T12:00:00Z",
		until: "2026-10-01T12:00:00Z",
		previous_since: "2026-08-02T12:00:00Z",
		alerts: {
			opened: { count: 12, previous: 9 },
			by_source: [
				{ key: "wazuh", label: null, count: 8, previous: 6 },
				{ key: "office365", label: null, count: 4, previous: 3 }
			],
			other_sources: { count: 0, previous: 0 },
			by_severity: [
				{ key: "Critical", label: null, count: 2, previous: 0 },
				{ key: "High", label: null, count: 10, previous: 9 },
				{ key: "Medium", label: null, count: 0, previous: 0 },
				{ key: "Low", label: null, count: 0, previous: 0 },
				{ key: "Informational", label: null, count: 0, previous: 0 }
			],
			top_detections: [{ key: "Brute force", label: null, count: 7, previous: 2 }],
			top_assets: [{ key: "web-01", label: null, count: 5, previous: 5 }],
			top_tags: [{ key: "vip", label: null, count: 3, previous: 4 }],
			error: null
		},
		verdicts: {
			current: {
				total: 12,
				reviewed: 8,
				true_positive: 6,
				false_positive: 2,
				untriaged: 4,
				false_positive_rate: 25,
				coverage_rate: 66.7
			},
			previous: {
				total: 9,
				reviewed: 0,
				true_positive: 0,
				false_positive: 0,
				untriaged: 9,
				false_positive_rate: null,
				coverage_rate: 0
			},
			reasons: [{ key: "RULE_TOO_SENSITIVE", label: "Detection rule too sensitive", count: 2, previous: 0 }],
			noisy_detections: [{ name: "Brute force", false_positives: 2, reviewed: 4, false_positive_rate: 50 }],
			error: null
		},
		cases: {
			opened: { count: 2, previous: 1 },
			by_type: [{ key: "INC", label: "Incident", count: 2, previous: 1 }],
			by_status: [{ key: "PENDING_CUSTOMER", label: null, count: 1, previous: 0 }],
			error: null
		},
		...over
	}
}
