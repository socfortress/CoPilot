import type { Compliance, DurationStats, PolicyMatrix, SocDashboard } from "../src/types/soc-management"

/**
 * One fixed SOC Management snapshot (#1187), shaped exactly like
 * `GET /soc_management/dashboard`. Numbers are chosen so each one is recognisable on
 * screen: if the page shows 1,284 it read `headline.alerts.opened`, nothing else.
 */

function stats(median: number | null, p90: number | null = null, mean: number | null = null): DurationStats {
	return {
		count: median == null ? 0 : 10,
		median,
		p90,
		mean
	}
}

function compliance(met: number, breached: number): Compliance {
	return {
		met,
		breached,
		at_risk: 0,
		on_track: 0,
		not_tracked: 0,
		decided: met + breached,
		rate: met + breached ? Math.round((met * 1000) / (met + breached)) / 10 : null
	}
}

const SEVERITIES = ["Critical", "High", "Medium", "Low", "Informational"] as const

export const POLICY: PolicyMatrix = {
	customer_code: null,
	cells: (["alert", "case"] as const).flatMap(entity =>
		SEVERITIES.map(severity => ({
			entity,
			severity,
			ack_minutes: severity === "Informational" ? null : severity === "Critical" ? 15 : 60,
			resolve_minutes: severity === "Informational" ? null : severity === "Critical" ? 240 : 480,
			source: severity === "High" && entity === "alert" ? ("global" as const) : ("default" as const)
		}))
	)
}

export function dashboard(over: Partial<SocDashboard> = {}): SocDashboard {
	return {
		generated_at: "2026-09-30T10:00:00",
		period: {
			date_from: "2026-08-31T10:00:00",
			date_to: "2026-09-30T10:00:00",
			previous_from: "2026-08-01T10:00:00",
			previous_to: "2026-08-31T10:00:00",
			bucket: "day"
		},
		viewer: { username: "admin", is_admin: true, sees_all_analysts: true },
		customer_codes: null,
		tracking_since: "2026-01-01T00:00:00",
		headline: {
			alerts: {
				opened: 1284,
				resolved: 1210,
				resolved_by_customer: 4,
				tta: stats(720, 2400, 900),
				ttr: stats(13_800, 90_000, 20_000),
				sla: { ack: compliance(980, 20), resolve: compliance(964, 36) },
				reopened: 3
			},
			cases: {
				opened: 42,
				resolved: 38,
				resolved_by_customer: 0,
				tta: stats(300),
				ttr: stats(86_400),
				sla: { ack: compliance(40, 0), resolve: compliance(36, 2) },
				reopened: 0
			},
			false_positive_rate: 31.5,
			reviewed_alerts: 900,
			case_conversion_rate: 3.3,
			escalated_alerts: 12
		},
		previous: {
			alerts: {
				opened: 1167,
				resolved: 1100,
				resolved_by_customer: 0,
				tta: stats(900),
				ttr: stats(15_000),
				sla: { ack: compliance(950, 50), resolve: compliance(940, 60) },
				reopened: 0
			},
			cases: {
				opened: 40,
				resolved: 39,
				resolved_by_customer: 0,
				tta: stats(300),
				ttr: stats(90_000),
				sla: { ack: compliance(40, 0), resolve: compliance(38, 2) },
				reopened: 0
			},
			false_positive_rate: 35,
			reviewed_alerts: 850,
			case_conversion_rate: 3.1,
			escalated_alerts: 10
		},
		severities: (["alert", "case"] as const).flatMap(entity =>
			SEVERITIES.map(severity => ({
				entity,
				severity,
				opened: severity === "High" ? 400 : 10,
				resolved: 9,
				open_now: 2,
				breached_now: severity === "Critical" ? 1 : 0,
				tta: stats(600, 1200),
				ttr: stats(7200, 20_000),
				sla: { ack: compliance(9, 1), resolve: compliance(8, 2) }
			}))
		),
		trends: Array.from({ length: 30 }, (_, i) => ({
			start: `2026-09-${String(i + 1).padStart(2, "0")}T00:00:00`,
			alerts_opened: 40 + (i % 7),
			alerts_resolved: 38 + (i % 5),
			cases_opened: i % 3,
			cases_resolved: i % 2,
			sla_rate: i % 6 === 0 ? null : 90 + (i % 9),
			alert_ttr_median: 13_000
		})),
		analysts: [
			{
				username: "ana",
				alerts_acknowledged: 410,
				alerts_resolved: 402,
				cases_acknowledged: 10,
				cases_resolved: 9,
				tta: stats(600),
				ttr: stats(12_000),
				sla: compliance(390, 12),
				open_alerts: 6,
				open_cases: 1,
				at_risk: 1,
				breached: 0
			},
			{
				username: "bob",
				alerts_acknowledged: 300,
				alerts_resolved: 290,
				cases_acknowledged: 5,
				cases_resolved: 4,
				tta: stats(1500),
				ttr: stats(20_000),
				sla: compliance(250, 40),
				open_alerts: 9,
				open_cases: 0,
				at_risk: 0,
				breached: 2
			}
		],
		rules: [
			{
				alert_name: "Brute force SSH login",
				sources: ["wazuh"],
				alerts: 512,
				in_case: 3,
				reviewed: 400,
				true_positives: 80,
				false_positives: 320,
				false_positive_rate: 80,
				noisy: true,
				open_now: 4,
				ttr: stats(3600),
				sla: compliance(500, 12),
				series: Array.from({ length: 30 }, (_, i) => 15 + (i % 4))
			},
			{
				alert_name: "Malware detected by EDR",
				sources: ["crowdstrike"],
				alerts: 31,
				in_case: 12,
				reviewed: 30,
				true_positives: 29,
				false_positives: 1,
				false_positive_rate: 3.3,
				noisy: false,
				open_now: 1,
				ttr: stats(9000),
				sla: compliance(30, 1),
				series: Array.from({ length: 30 }, (_, i) => i % 2)
			}
		],
		customers: [
			{
				customer_code: "ACME",
				customer_name: "Acme Corp",
				alerts: 1000,
				cases: 30,
				resolved: 990,
				open_now: 12,
				breached_now: 1,
				alert_ttr: stats(13_000),
				case_ttr: stats(80_000),
				alert_sla: compliance(960, 40),
				case_sla: compliance(28, 2),
				top_rule: "Brute force SSH login"
			}
		],
		workload: {
			open_alerts: 15,
			open_cases: 1,
			unassigned_alerts: 3,
			unassigned_cases: 0,
			oldest_unassigned_at: "2026-09-30T06:00:00",
			breached: 2,
			at_risk: 1,
			by_severity: SEVERITIES.map(severity => ({ severity, alerts: 3, cases: 0, breached: 0, at_risk: 0 })),
			by_assignee: [
				{ username: "ana", alerts: 6, cases: 1, breached: 0, at_risk: 1 },
				{ username: "bob", alerts: 9, cases: 0, breached: 2, at_risk: 0 }
			]
		},
		attention: [
			{
				entity: "alert",
				id: 4711,
				title: "Ransomware note dropped",
				customer_code: "ACME",
				severity: "Critical",
				status: "OPEN",
				assigned_to: null,
				opened_at: "2026-09-30T08:00:00",
				state: "breached",
				clock: "ack",
				due_at: "2026-09-30T08:15:00",
				overdue_seconds: 6300
			},
			{
				entity: "case",
				id: 12,
				title: "Lateral movement investigation",
				customer_code: "ACME",
				severity: "High",
				status: "IN_PROGRESS",
				assigned_to: "ana",
				opened_at: "2026-09-30T02:00:00",
				state: "at_risk",
				clock: "resolve",
				due_at: "2026-09-30T10:30:00",
				overdue_seconds: -1800
			}
		],
		policy: POLICY,
		...over
	}
}
