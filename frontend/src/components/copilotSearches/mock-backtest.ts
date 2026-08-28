/**
 * Dev-only "everything at once" backtest result.
 *
 * Purpose: the backtest modal is almost entirely conditional — the threshold
 * simulation only renders in aggregation mode, top offenders and the sensitivity
 * strip only when the backend returns them, the missing-fields and note alerts
 * only on specific tenants, and the event inspector's internal-fields collapse
 * only when a sample carries `gl2_*` keys. No single real rule against a real
 * tenant lights all of that up at once, so reviewing a layout change here meant
 * hunting for a rule + customer combination that happened to hit the branch you
 * touched. This fixture populates every branch in one response.
 *
 * Turn it on with MOCK_BACKTEST_ENABLED below, open the editor, hit "Backtest",
 * pick any customer and run — the request never leaves the browser.
 *
 * It lives next to the component it feeds rather than in src/dev/, so the fixture
 * is found by whoever is editing the modal it describes. It stays dev-only through
 * USE_MOCK_BACKTEST, not through where it sits.
 */

import type { BacktestResponse, BacktestTopValue } from "@/types/copilot-searches"

/**
 * The switch. Set to false to turn the fixture off without removing any code —
 * "Run backtest" then goes back to the real API like any other run.
 */
const MOCK_BACKTEST_ENABLED = false

/**
 * Guarded by DEV as well, so the fixture cannot serve data from a production
 * build even if this file is left enabled.
 */
export const USE_MOCK_BACKTEST = import.meta.env.DEV && MOCK_BACKTEST_ENABLED

/**
 * How long the fixture pretends to query Graylog, so the running spinner is
 * actually on screen while reviewing this modal.
 */
export const MOCK_LATENCY_MS = 1100

/**
 * Fields the samples table builds its columns from — deliberately more than the
 *  six the table slices to, so the truncation is exercised too.
 */
const SAMPLE_FIELDS = [
	"timestamp",
	"source",
	"data_win_eventdata_targetUserName",
	"data_win_eventdata_ipAddress",
	"data_win_system_eventID",
	"rule_level",
	"agent_labels_customer",
	"data_win_eventdata_logonType"
]

const USERS = ["svc_backup", "j.rivera", "administrator", "m.okafor", "svc_sql", "d.laurent"]
const HOSTS = ["WIN-DC01", "WIN-FS02", "WIN-APP07", "WIN-DC02"]
const IPS = ["10.14.22.8", "10.14.9.140", "192.168.44.21", "10.14.22.51", "203.0.113.77"]

function topValues(pairs: [string, number][]): BacktestTopValue[] {
	return pairs.map(([value, count]) => ({ value, count }))
}

/**
 * One sample event. Carries every group the inspector splits on: the PRIMARY_ORDER
 * keys, a spread of ordinary fields, and the `gl2_*` / `streams` internals that put
 * the "Graylog internal fields" collapse on screen.
 */
function sampleEvent(i: number): Record<string, unknown> {
	const at = new Date(Date.now() - i * 37 * 60_000)
	const user = USERS[i % USERS.length]
	const host = HOSTS[i % HOSTS.length]
	const ip = IPS[i % IPS.length]
	return {
		timestamp: at.toISOString(),
		source: host,
		message: `An account failed to log on. Account Name: ${user} Source Network Address: ${ip}`,
		full_message:
			`An account failed to log on.\n\nSubject:\n\tSecurity ID:\t\tS-1-5-18\n\tAccount Name:\t\t${host}$\n\t` +
			`Account Domain:\t\tCORP\n\nLogon Type:\t\t3\n\nAccount For Which Logon Failed:\n\t` +
			`Account Name:\t\t${user}\n\tAccount Domain:\t\tCORP\n\nFailure Information:\n\t` +
			`Failure Reason:\t\tUnknown user name or bad password.\n\tStatus:\t\t\t0xC000006D\n\t` +
			`Sub Status:\t\t0xC000006A\n\nNetwork Information:\n\tSource Network Address:\t${ip}\n\tSource Port:\t\t${44000 + i}`,
		data_win_eventdata_targetUserName: user,
		data_win_eventdata_ipAddress: ip,
		data_win_eventdata_logonType: "3",
		data_win_eventdata_workstationName: host,
		data_win_system_eventID: "4625",
		data_win_system_channel: "Security",
		data_win_system_computer: `${host.toLowerCase()}.corp.local`,
		rule_level: 5 + (i % 4),
		rule_id: "60122",
		rule_description: "Logon failure - Unknown user or bad password",
		agent_labels_customer: "00001",
		agent_name: host.toLowerCase(),
		// Graylog internals — these are what the inspector folds into its collapse
		gl2_accounted_message_size: 1284 + i,
		gl2_message_id: `01JQ8X${String(i).padStart(2, "0")}ZK4M7PBV3N6TQ9WYRD`,
		gl2_processing_timestamp: at.toISOString(),
		gl2_receive_timestamp: at.toISOString(),
		gl2_remote_ip: "10.14.0.4",
		gl2_source_input: "66f1a0c3e4b9d2110a8c4471",
		gl2_source_node: "a7c1e9f2-5b3d-4e88-9c02-1f6b7d40ae35",
		streams: ["000000000000000000000001", "66f1a0c3e4b9d2110a8c44a2"]
	}
}

/**
 * Buckets across the picked look-back. Short ranges bucket hourly and long ones
 * daily, matching the backend — which also means switching the Look-back select
 * exercises both labels the sparkline heading can render.
 */
function buildBuckets(rangeSeconds: number): { bucket: string; count: number }[] {
	const hourly = rangeSeconds <= 259_200
	const stepMs = hourly ? 3_600_000 : 86_400_000
	const steps = Math.max(6, Math.round((rangeSeconds * 1000) / stepMs))
	const now = Date.now()
	const out: { bucket: string; count: number }[] = []
	for (let i = steps - 1; i >= 0; i--) {
		const at = new Date(now - i * stepMs)
		// A quiet baseline with a working-hours swell and one obvious spike, so the
		// chart has a shape worth looking at instead of noise.
		const hour = at.getUTCHours()
		const business = hour >= 7 && hour <= 19 ? 1 : 0.35
		const spike = i === Math.floor(steps * 0.28) ? 6 : 1
		const wobble = ((i * 37) % 11) / 11
		const base = hourly ? 14 : 260
		out.push({
			bucket: at.toISOString(),
			count: Math.round(base * business * spike * (0.6 + wobble))
		})
	}
	return out
}

/** A fully-populated, successful aggregation backtest. */
export function mockBacktest(customerCode: string, rangeSeconds: number): BacktestResponse {
	const perBucket = buildBuckets(rangeSeconds)
	const totalHits = perBucket.reduce((acc, b) => acc + b.count, 0)
	const days = Math.max(1, Math.round(rangeSeconds / 86_400))

	return {
		success: true,
		message: "Backtest completed",
		error: null,
		// Aggregation mode is the strictly richer branch: it adds the whole threshold
		// simulation section on top of everything the messages mode renders.
		mode: "aggregation",
		customer_code: customerCode,
		stream_id: "66f1a0c3e4b9d2110a8c44a2",
		query: 'data_win_system_eventID:"4625" AND NOT data_win_eventdata_targetUserName:"ANONYMOUS LOGON"',
		range_seconds: rangeSeconds,
		total_hits: totalHits,
		per_day_avg: Math.round(totalHits / days),
		fetched: Math.min(totalHits, 5000),
		truncated: true,
		per_bucket: perBucket,
		bucket_unit: rangeSeconds <= 259_200 ? "1h" : "1d",
		samples: Array.from({ length: 8 }, (_, i) => sampleEvent(i)),
		sample_fields: SAMPLE_FIELDS,
		top_fields: {
			data_win_eventdata_targetUserName: topValues([
				["svc_backup", 412],
				["administrator", 288],
				["j.rivera", 143],
				["svc_sql", 96],
				["m.okafor", 41]
			]),
			data_win_eventdata_ipAddress: topValues([
				["10.14.22.8", 508],
				["203.0.113.77", 214],
				["10.14.9.140", 122],
				["192.168.44.21", 88],
				["10.14.22.51", 34]
			]),
			source: topValues([
				["WIN-DC01", 611],
				["WIN-FS02", 232],
				["WIN-APP07", 118],
				["WIN-DC02", 45]
			]),
			data_win_eventdata_logonType: topValues([
				["3", 802],
				["10", 149],
				["2", 55]
			])
		},
		aggregation: {
			window: "10m",
			window_seconds: 600,
			function: "count",
			field: null,
			group_by: ["data_win_eventdata_targetUserName", "data_win_eventdata_ipAddress"],
			threshold: 30,
			condition: ">",
			estimated_alerts: 47,
			per_day_alerts: Math.max(1, Math.round(47 / days)),
			top_offenders: [
				{ group: "svc_backup · 10.14.22.8", windows_alerting: 18, peak: 214 },
				{ group: "administrator · 203.0.113.77", windows_alerting: 12, peak: 168 },
				{ group: "j.rivera · 10.14.9.140", windows_alerting: 9, peak: 91 },
				{ group: "svc_sql · 192.168.44.21", windows_alerting: 5, peak: 54 },
				{ group: "m.okafor · 10.14.22.51", windows_alerting: 3, peak: 38 }
			],
			sensitivity: [
				{ threshold: 10, alerts: 214 },
				{ threshold: 20, alerts: 96 },
				// Matches `threshold` above so the outlined "current setting" chip renders.
				{ threshold: 30, alerts: 47 },
				{ threshold: 50, alerts: 12 },
				{ threshold: 100, alerts: 3 }
			],
			truncated: false
		},
		missing_fields: ["data_win_eventdata_privilegeList", "data_win_eventdata_processName"],
		note: "Sampled 5,000 of 12,480 matching events — top values and the threshold simulation are extrapolated from the sample."
	}
}
