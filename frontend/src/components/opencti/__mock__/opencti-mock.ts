/* eslint-disable ts/no-non-null-assertion -- throwaway mock data, deleted before merge */
// ============================================================================
// TEMPORARY MOCK — UI/UX review only. Delete this file and restore the
// `Api.opencti` imports in OpenCTIPlatformStats / OpenCTIForm /
// OpenCTIIndicatorsIndex / OpenCTIEntityDetail / useOpenCTIAvailability
// before merging.
//
// Mirrors the `Api.opencti` surface (same method names, same `{ data }`
// envelope) so the components stay byte-identical apart from the import.
// Search / type / min-score filters and cursor pagination are implemented
// client-side so every interactive path of the UI can be exercised.
//
// Special lookup values (IOC Lookup tab):
//   "error"              → rejected request (error state)
//   "slow"               → 4 s delay (long spinner)
//   "1.2.3.4"            → not found
//   "sdk.netnut.io"      → 2 observables (Domain-Name + Hostname) with the
//                          "Showing 2 of 5" footer
//   "45.155.205.233"     → rich IPv4 (indicators, reports, TLP:AMBER)
//   "<sha256 below>"     → file with md5 / sha1 / sha256 + file_name
//   "http://185.220.101.47/gate.php" → URL
//   "invoice@dhl-express-delivery.com" → email
//   "long"               → observable with a very long value / many labels
//   anything else        → a generic Domain-Name observable
// Search box (Indicators tab):
//   "error"    → error state
//   "empty"    → 0 rows (empty table)
//   "slow"     → 4 s delay: with rows on screen the table spins, with none the
//                Search button spins
//   "nocount"  → page_info.global_count = null (footer count hidden)
//   "deleted"  → the one row whose detail drawer fails (entity not found)
// Row edge cases in the table: name→pattern→id fallbacks, type "—", score
// null / 0 / 49 / 75 / 100, 0 and 7 labels (+4), author "—", created "—",
// validity valid / expired / revoked / no expiry. Load more → 6 pages.
// ============================================================================

import type {
	OpenCTIAbout,
	OpenCTIAvailability,
	OpenCTIEntity,
	OpenCTIIndicator,
	OpenCTIIndicatorsQuery,
	OpenCTILabel,
	OpenCTIObservable,
	OpenCTIObservableLookup,
	OpenCTIPageInfo,
	OpenCTIReportRef
} from "@/types/opencti"

const DEFAULT_DELAY_MS = 600

export const MOCK_PLATFORM_URL = "https://opencti.socfortress.example"

const SHA256 = "3395856ce81f2b7382dee72602f798b642f14140f9ea0d0a5a1fa7e2f7f1a9d2"
const SHA1 = "3395856ce81f2b7382dee72602f798b642f14140"
const MD5 = "44d88612fea8a8f36de82e1278abb02f"

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function wait<T>(value: T, ms = DEFAULT_DELAY_MS): Promise<{ data: T }> {
	return new Promise(resolve => setTimeout(resolve, ms, { data: value }))
}

function fail(message: string, ms = DEFAULT_DELAY_MS): Promise<never> {
	return new Promise((_, reject) =>
		setTimeout(reject, ms, {
			response: { status: 502, data: { success: false, message } },
			message
		})
	)
}

function daysAgo(days: number, hours = 0): string {
	return new Date(Date.now() - (days * 24 + hours) * 3600 * 1000).toISOString()
}

function daysAhead(days: number): string {
	return daysAgo(-days)
}

function label(value: string, color: string | null = null): OpenCTILabel {
	return { value, color }
}

// Deterministic PRNG so the generated rows are stable across reloads.
function mulberry32(seed: number) {
	return () => {
		seed |= 0
		seed = (seed + 0x6D2B79F5) | 0
		let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296
	}
}

// ---------------------------------------------------------------------------
// static vocabulary
// ---------------------------------------------------------------------------

const LABELS: OpenCTILabel[] = [
	label("malware", "#d32f2f"),
	label("c2", "#b71c1c"),
	label("phishing", "#f57c00"),
	label("cobalt-strike", "#7b1fa2"),
	label("qakbot", "#6a1b9a"),
	label("emotet", "#4a148c"),
	label("lockbit", "#212121"),
	label("ransomware", "#000000"),
	label("apt29", "#1565c0"),
	label("apt28", "#0d47a1"),
	label("tor-exit-node", "#455a64"),
	label("scanner", "#78909c"),
	label("bulletproof-hosting", "#5d4037"),
	label("credential-harvesting", "#e65100"),
	label("misp", "#2e7d32"),
	label("osint", "#00897b"),
	label("feodo", "#c62828"),
	label("urlhaus", "#ad1457"),
	label("abuse.ch", "#00838f"),
	label("high-confidence", "#1b5e20"),
	label("needs-review", "#9e9d24")
]

const AUTHORS = [
	"AlienVault OTX",
	"abuse.ch",
	"MISP Feed",
	"CISA",
	"Mandiant",
	"SOCFortress Threat Intel",
	"Recorded Future",
	"CrowdStrike Falcon Intelligence",
	"Internal Research",
	null
]

const MARKINGS = [
	["TLP:CLEAR"],
	["TLP:GREEN"],
	["TLP:AMBER"],
	["TLP:AMBER+STRICT"],
	["TLP:RED"],
	[],
	["TLP:GREEN", "PAP:GREEN"]
]

const TYPES = ["IPv4-Addr", "IPv6-Addr", "Domain-Name", "Hostname", "Url", "StixFile", "Email-Addr"] as const

// ---------------------------------------------------------------------------
// indicators (hand-authored edge cases + generated volume)
// ---------------------------------------------------------------------------

function indicator(partial: Partial<OpenCTIIndicator> & { id: string }): OpenCTIIndicator {
	return {
		standard_id: `indicator--${partial.id.replace(/^ind-/, "")}`,
		entity_type: "Indicator",
		created_at: daysAgo(10),
		updated_at: daysAgo(1),
		created_by: "abuse.ch",
		labels: [],
		markings: ["TLP:CLEAR"],
		name: null,
		description: null,
		pattern: null,
		pattern_type: "stix",
		main_observable_type: null,
		score: null,
		confidence: null,
		valid_from: daysAgo(10),
		valid_until: daysAhead(80),
		revoked: false,
		...partial
	}
}

const HAND_AUTHORED: OpenCTIIndicator[] = [
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000001",
		name: "45.155.205.233",
		pattern: "[ipv4-addr:value = '45.155.205.233']",
		main_observable_type: "IPv4-Addr",
		score: 95,
		confidence: 90,
		created_by: "abuse.ch",
		labels: [LABELS[1], LABELS[3], LABELS[16], LABELS[19]],
		markings: ["TLP:AMBER"],
		description:
			"Cobalt Strike Beacon C2 hosted on bulletproof infrastructure (AS-CHOOPA). Observed in three separate intrusions targeting European financial services in Q2/Q3 2026.",
		created_at: daysAgo(2),
		updated_at: daysAgo(0, 3),
		valid_from: daysAgo(2),
		valid_until: daysAhead(28)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000002",
		name: "sdk.netnut.io",
		pattern: "[domain-name:value = 'sdk.netnut.io']",
		main_observable_type: "Domain-Name",
		score: 60,
		confidence: 50,
		created_by: "AlienVault OTX",
		labels: [LABELS[11], LABELS[15]],
		markings: ["TLP:CLEAR"],
		description:
			"Residential proxy SDK endpoint. Frequently abused for credential-stuffing traffic; benign in some consumer apps.",
		created_at: daysAgo(45),
		updated_at: daysAgo(12),
		valid_until: daysAhead(5)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000003",
		name: `${SHA256}`,
		pattern: `[file:hashes.'SHA-256' = '${SHA256}']`,
		main_observable_type: "StixFile",
		score: 100,
		confidence: 100,
		created_by: "Mandiant",
		labels: [LABELS[0], LABELS[6], LABELS[7]],
		markings: ["TLP:RED"],
		description:
			"LockBit 3.0 (Black) payload. Encryptor build 2026-07-14. Kills VSS, disables Defender via TamperProtection bypass.",
		created_at: daysAgo(1),
		updated_at: daysAgo(1),
		valid_from: daysAgo(1),
		valid_until: daysAhead(365)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000004",
		name: "http://185.220.101.47/gate.php",
		pattern: "[url:value = 'http://185.220.101.47/gate.php']",
		main_observable_type: "Url",
		score: 80,
		confidence: 75,
		created_by: "MISP Feed",
		labels: [LABELS[4], LABELS[17]],
		markings: ["TLP:GREEN"],
		created_at: daysAgo(90),
		updated_at: daysAgo(60),
		valid_until: daysAgo(3) // EXPIRED but not revoked
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000005",
		name: "invoice@dhl-express-delivery.com",
		pattern: "[email-addr:value = 'invoice@dhl-express-delivery.com']",
		main_observable_type: "Email-Addr",
		score: 70,
		confidence: 60,
		created_by: "SOCFortress Threat Intel",
		labels: [LABELS[2], LABELS[13]],
		markings: ["TLP:AMBER+STRICT"],
		description: "Sender of DHL-themed phishing wave, 2026-08. HTML attachment with embedded JS smuggling.",
		created_at: daysAgo(30),
		updated_at: daysAgo(30),
		valid_until: daysAhead(60)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000006",
		name: "2a02:c207:2033:7812::1",
		pattern: "[ipv6-addr:value = '2a02:c207:2033:7812::1']",
		main_observable_type: "IPv6-Addr",
		score: 40,
		confidence: 30,
		created_by: "Internal Research",
		labels: [LABELS[10]],
		markings: [],
		created_at: daysAgo(200),
		updated_at: daysAgo(200),
		valid_until: null // no expiry
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000007",
		name: "old-c2.emotet-epoch4.example",
		pattern: "[domain-name:value = 'old-c2.emotet-epoch4.example']",
		main_observable_type: "Domain-Name",
		score: 20,
		confidence: 15,
		created_by: "abuse.ch",
		labels: [LABELS[5], LABELS[0]],
		markings: ["TLP:CLEAR"],
		created_at: daysAgo(400),
		updated_at: daysAgo(100),
		valid_until: daysAgo(100),
		revoked: true // REVOKED
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000008",
		// No name at all → the table must fall back to the pattern
		name: null,
		pattern:
			"[windows-registry-key:key = 'HKEY_CURRENT_USER\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run\\\\OneDriveUpdater']",
		pattern_type: "stix",
		main_observable_type: "Windows-Registry-Key",
		score: 55,
		confidence: 40,
		created_by: "CrowdStrike Falcon Intelligence",
		labels: [LABELS[4]],
		markings: ["TLP:AMBER"],
		created_at: daysAgo(7),
		updated_at: daysAgo(7)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000009",
		// No name, no pattern → falls back to the id
		name: null,
		pattern: null,
		pattern_type: "yara",
		main_observable_type: null,
		score: null,
		confidence: null,
		created_by: null,
		labels: [],
		markings: [],
		created_at: null,
		updated_at: null,
		valid_from: null,
		valid_until: null,
		revoked: null
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000010",
		name: 'rule APT29_WellMess_Loader : apt29 wellmess { strings: $a = "WellMess" $b = { 48 8B 05 ?? ?? ?? ?? 48 85 C0 } condition: uint16(0) == 0x5A4D and all of them }',
		pattern:
			'rule APT29_WellMess_Loader : apt29 wellmess { meta: author = "NCSC" strings: $a = "WellMess" $b = { 48 8B 05 ?? ?? ?? ?? 48 85 C0 } condition: uint16(0) == 0x5A4D and all of them }',
		pattern_type: "yara",
		main_observable_type: "StixFile",
		score: 85,
		confidence: 80,
		created_by: "CISA",
		labels: [LABELS[8], LABELS[0], LABELS[14], LABELS[19], LABELS[20], LABELS[9], LABELS[15]], // 7 labels → "+4"
		markings: ["TLP:GREEN", "PAP:GREEN"],
		description:
			"YARA rule for the WellMess loader attributed to APT29. Long-name row to test truncation and tooltips.",
		created_at: daysAgo(15),
		updated_at: daysAgo(2)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000011",
		name: "login-microsoftonline-com.secure-auth-portal-verification-services-eu-west.cloudfront-cdn-assets.net",
		pattern:
			"[domain-name:value = 'login-microsoftonline-com.secure-auth-portal-verification-services-eu-west.cloudfront-cdn-assets.net']",
		main_observable_type: "Domain-Name",
		score: 90,
		confidence: 85,
		created_by: "Recorded Future",
		labels: [LABELS[2], LABELS[13]],
		markings: ["TLP:AMBER"],
		created_at: daysAgo(0, 6),
		updated_at: daysAgo(0, 1),
		valid_until: daysAhead(14)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000012",
		name: "0.0.0.0/8",
		pattern: "[ipv4-addr:value ISSUBSET '0.0.0.0/8']",
		main_observable_type: "IPv4-Addr",
		score: 0,
		confidence: 0,
		created_by: "Internal Research",
		labels: [LABELS[20]],
		markings: ["TLP:CLEAR"],
		description: "Score 0 boundary case — a whitelisted range kept for suppression testing.",
		created_at: daysAgo(3),
		updated_at: daysAgo(3)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000013",
		name: "75-boundary.example",
		pattern: "[domain-name:value = '75-boundary.example']",
		main_observable_type: "Domain-Name",
		score: 75, // exactly at HIGH_SCORE threshold
		confidence: 50,
		labels: [LABELS[14]],
		created_at: daysAgo(5),
		updated_at: daysAgo(5)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000014",
		name: "49-boundary.example",
		pattern: "[domain-name:value = '49-boundary.example']",
		main_observable_type: "Domain-Name",
		score: 49, // just under the warning threshold
		confidence: 50,
		labels: [LABELS[14]],
		created_at: daysAgo(5),
		updated_at: daysAgo(5)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000016",
		// Entity lookup for this row fails: exercises the drawer's error state.
		name: "deleted-entity.example",
		pattern: "[domain-name:value = 'deleted-entity.example']",
		main_observable_type: "Domain-Name",
		score: 10,
		confidence: 10,
		labels: [LABELS[20]],
		created_at: daysAgo(1),
		updated_at: daysAgo(1)
	}),
	indicator({
		id: "ind-c0ffee00-0000-4000-8000-000000000015",
		name: "expires-today.example",
		pattern: "[domain-name:value = 'expires-today.example']",
		main_observable_type: "Domain-Name",
		score: 65,
		confidence: 55,
		labels: [LABELS[2]],
		created_at: daysAgo(30),
		updated_at: daysAgo(1),
		valid_until: daysAgo(0, 1) // expired an hour ago
	})
]

function generateIndicators(count: number, seed = 42): OpenCTIIndicator[] {
	const rnd = mulberry32(seed)
	const pick = <T>(arr: readonly T[]): T => arr[Math.floor(rnd() * arr.length)] as T
	const out: OpenCTIIndicator[] = []

	for (let i = 0; i < count; i++) {
		const type = pick(TYPES)
		let value: string
		let pattern: string
		switch (type) {
			case "IPv4-Addr":
				value = `${Math.floor(rnd() * 223) + 1}.${Math.floor(rnd() * 255)}.${Math.floor(rnd() * 255)}.${Math.floor(rnd() * 254) + 1}`
				pattern = `[ipv4-addr:value = '${value}']`
				break
			case "IPv6-Addr":
				value = `2a0${Math.floor(rnd() * 9)}:${Math.floor(rnd() * 0xFFFF).toString(16)}:${Math.floor(rnd() * 0xFFFF).toString(16)}::${Math.floor(rnd() * 0xFF).toString(16)}`
				pattern = `[ipv6-addr:value = '${value}']`
				break
			case "Domain-Name":
				value = `${pick(["cdn", "update", "secure", "mail", "api", "static", "login", "portal"])}-${Math.floor(rnd() * 9000 + 1000)}.${pick(["xyz", "top", "click", "live", "icu", "buzz", "shop"])}`
				pattern = `[domain-name:value = '${value}']`
				break
			case "Hostname":
				value = `${pick(["ns1", "vpn", "srv", "mx", "gw"])}.${pick(["darkhost", "shadowlab", "nightwire"])}-${Math.floor(rnd() * 900 + 100)}.net`
				pattern = `[hostname:value = '${value}']`
				break
			case "Url":
				value = `http${rnd() > 0.5 ? "s" : ""}://${Math.floor(rnd() * 223) + 1}.${Math.floor(rnd() * 255)}.${Math.floor(rnd() * 255)}.${Math.floor(rnd() * 254) + 1}/${pick(["gate.php", "panel/login", "bot/update.exe", "dl/inv.zip", "wp-content/x.php"])}`
				pattern = `[url:value = '${value}']`
				break
			case "StixFile": {
				let hex = ""
				for (let h = 0; h < 64; h++) hex += Math.floor(rnd() * 16).toString(16)
				value = hex
				pattern = `[file:hashes.'SHA-256' = '${hex}']`
				break
			}
			case "Email-Addr":
			default:
				value = `${pick(["billing", "hr", "invoice", "support", "ceo"])}${Math.floor(rnd() * 99)}@${pick(["paypa1-secure", "micros0ft-support", "dhl-track", "amaz0n-orders"])}.com`
				pattern = `[email-addr:value = '${value}']`
		}

		const created = Math.floor(rnd() * 365)
		const labelCount = Math.floor(rnd() * 5)
		const labels: OpenCTILabel[] = []
		for (let l = 0; l < labelCount; l++) {
			const cand = pick(LABELS)
			if (!labels.some(x => x.value === cand.value)) labels.push(cand)
		}
		const scoreRoll = rnd()
		const score = scoreRoll < 0.1 ? null : Math.floor(rnd() * 101)
		const validRoll = rnd()

		out.push(
			indicator({
				id: `ind-gen-${String(i).padStart(4, "0")}-4000-8000-${String(i * 7919).padStart(12, "0")}`,
				name: value,
				pattern,
				main_observable_type: type,
				score,
				confidence: score === null ? null : Math.max(0, Math.min(100, score - Math.floor(rnd() * 30))),
				created_by: pick(AUTHORS),
				labels,
				markings: pick(MARKINGS),
				description:
					rnd() > 0.6 ? `Auto-generated indicator #${i} from ${pick(AUTHORS) ?? "unknown feed"}.` : null,
				created_at: daysAgo(created),
				updated_at: daysAgo(Math.floor(created * rnd())),
				valid_from: daysAgo(created),
				valid_until:
					validRoll < 0.15
						? null
						: validRoll < 0.3
							? daysAgo(Math.floor(rnd() * 60))
							: daysAhead(Math.floor(rnd() * 180)),
				revoked: rnd() < 0.07
			})
		)
	}
	return out
}

export const MOCK_INDICATORS: OpenCTIIndicator[] = [...HAND_AUTHORED, ...generateIndicators(118)]

// ---------------------------------------------------------------------------
// observables (IOC lookup)
// ---------------------------------------------------------------------------

function report(id: string, name: string | null, published: string | null): OpenCTIReportRef {
	return { id, name, published }
}

function observable(partial: Partial<OpenCTIObservable> & { id: string; entity_type: string }): OpenCTIObservable {
	return {
		standard_id: `${partial.entity_type.toLowerCase()}--${partial.id}`,
		created_at: daysAgo(20),
		updated_at: daysAgo(2),
		created_by: "abuse.ch",
		labels: [],
		markings: ["TLP:CLEAR"],
		value: null,
		description: null,
		score: null,
		file_name: null,
		hashes: [],
		indicators: [],
		indicators_count: 0,
		reports: [],
		reports_count: 0,
		...partial
	}
}

const OBS_IPV4 = observable({
	id: "obs-0001",
	entity_type: "IPv4-Addr",
	value: "45.155.205.233",
	score: 95,
	created_by: "abuse.ch",
	markings: ["TLP:AMBER"],
	labels: [LABELS[1], LABELS[3], LABELS[16], LABELS[12], LABELS[19]],
	description:
		"Cobalt Strike Beacon C2 on AS-CHOOPA (bulletproof). First seen 2026-06-03 in a Qakbot → Cobalt Strike hand-off; re-used in August against two EU banks. Also observed serving a Feodo tracker listing.",
	indicators: [
		HAND_AUTHORED[0]!,
		{ ...HAND_AUTHORED[6]!, name: "45.155.205.233 (legacy)", pattern: "[ipv4-addr:value = '45.155.205.233']" }
	],
	indicators_count: 6, // more than listed → "+4 more in OpenCTI"
	reports: [
		report("rep-0001", "Cobalt Strike infrastructure clustering — Q3 2026", daysAgo(4)),
		report("rep-0002", "Intrusion report: FIN-EU-2026-0812 (initial access via Qakbot)", daysAgo(20)),
		report("rep-0003", null, daysAgo(200)) // unnamed report
	],
	reports_count: 3
})

const OBS_DOMAIN = observable({
	id: "obs-0002",
	entity_type: "Domain-Name",
	value: "sdk.netnut.io",
	score: 60,
	created_by: "AlienVault OTX",
	markings: ["TLP:CLEAR"],
	labels: [LABELS[11], LABELS[15]],
	description: "Residential proxy SDK endpoint. Abused for credential stuffing; benign in some consumer apps.",
	indicators: [HAND_AUTHORED[1]!],
	indicators_count: 1,
	reports: [report("rep-0004", "Residential proxy networks as an evasion layer", daysAgo(60))],
	reports_count: 1
})

const OBS_HOSTNAME = observable({
	id: "obs-0003",
	entity_type: "Hostname",
	value: "sdk.netnut.io",
	score: null,
	created_by: null,
	markings: [],
	labels: [],
	indicators: [],
	indicators_count: 0,
	reports: [],
	reports_count: 0
})

const OBS_FILE = observable({
	id: "obs-0004",
	entity_type: "StixFile",
	value: null,
	file_name: "Invoice_2026-09_DHL_Express.pdf.exe",
	score: 100,
	created_by: "Mandiant",
	markings: ["TLP:RED"],
	labels: [LABELS[0], LABELS[6], LABELS[7]],
	description:
		"LockBit 3.0 encryptor. Detonated in CAPE: deletes shadow copies, disables Defender, drops ransom note in every directory.",
	hashes: [
		{ algorithm: "MD5", hash: MD5 },
		{ algorithm: "SHA-1", hash: SHA1 },
		{ algorithm: "SHA-256", hash: SHA256 }
	],
	indicators: [HAND_AUTHORED[2]!],
	indicators_count: 1,
	reports: [
		report("rep-0005", "LockBit 3.0 build analysis (2026-07-14)", daysAgo(1)),
		report("rep-0006", "Ransomware landscape — August 2026", daysAgo(15))
	],
	reports_count: 5 // more than listed → "+3 more in OpenCTI"
})

const OBS_URL = observable({
	id: "obs-0005",
	entity_type: "Url",
	value: "http://185.220.101.47/gate.php",
	score: 80,
	created_by: "MISP Feed",
	markings: ["TLP:GREEN"],
	labels: [LABELS[4], LABELS[17]],
	indicators: [HAND_AUTHORED[3]!],
	indicators_count: 1,
	reports: [],
	reports_count: 0
})

const OBS_EMAIL = observable({
	id: "obs-0006",
	entity_type: "Email-Addr",
	value: "invoice@dhl-express-delivery.com",
	score: 70,
	created_by: "SOCFortress Threat Intel",
	markings: ["TLP:AMBER+STRICT"],
	labels: [LABELS[2], LABELS[13]],
	indicators: [HAND_AUTHORED[4]!],
	indicators_count: 1,
	reports: [report("rep-0007", "DHL-themed phishing wave, 2026-08", daysAgo(28))],
	reports_count: 1
})

const OBS_LONG = observable({
	id: "obs-0007",
	entity_type: "Url",
	value: "https://login-microsoftonline-com.secure-auth-portal-verification-services-eu-west.cloudfront-cdn-assets.net/common/oauth2/v2.0/authorize?client_id=4765445b-32c6-49b0-83e6-1d93765276ca&redirect_uri=https%3A%2F%2Fwww.office.com%2Flandingv2&response_type=code%20id_token&scope=openid%20profile%20offline_access&state=cbzv7CbcSbeuSt2JQPY8XvijEAX9M5wu&nonce=1a2b3c4d5e6f",
	score: 90,
	created_by: "Recorded Future",
	markings: ["TLP:AMBER"],
	labels: LABELS, // every label
	description:
		"Adversary-in-the-middle phishing kit (EvilProxy) mimicking the Microsoft login flow. This description is intentionally long to check wrapping, line height and vertical rhythm inside the card. It continues over several lines so that the reviewer can judge whether a description this size needs a 'show more' affordance or whether a plain paragraph is fine.\n\nSecond paragraph after a blank line.",
	indicators: [HAND_AUTHORED[10]!, HAND_AUTHORED[9]!, HAND_AUTHORED[3]!, HAND_AUTHORED[13]!],
	indicators_count: 9, // more than listed
	reports: [
		report(
			"rep-0008",
			"EvilProxy: AiTM phishing-as-a-service — infrastructure & TTPs (very long report title that should wrap gracefully)",
			daysAgo(3)
		),
		report("rep-0009", "Weekly TI digest 2026-W37", daysAgo(5)),
		report("rep-0010", "Weekly TI digest 2026-W36", daysAgo(12)),
		report("rep-0011", "Weekly TI digest 2026-W35", daysAgo(19)),
		report("rep-0012", null, null)
	],
	reports_count: 12
})

function genericObservable(value: string): OpenCTIObservable {
	const slug = value.replace(/[^a-z0-9]/gi, "").slice(0, 16)
	return observable({
		id: `obs-generic-${slug}`,
		entity_type: "Domain-Name",
		value,
		score: 30,
		created_by: "MISP Feed",
		markings: ["TLP:GREEN", "PAP:AMBER"],
		// Mixed label set: coloured, near-black, and two with no colour at all
		// (the dot must fall back to the border tint, not vanish).
		labels: [LABELS[15], LABELS[11], LABELS[7], label("uncoloured-label"), label("sinkholed"), LABELS[20]],
		description: `${value} was first reported by a community MISP feed as part of a low-confidence cluster of sinkholed domains. It has not been observed in any confirmed intrusion; the score reflects feed reputation only.\n\nSecond paragraph: the entry is kept for correlation — a hit on this value in proxy or DNS logs is worth a look but not, on its own, an incident. This text is intentionally long enough to be clamped so the "Show more" control is exercised on every generic lookup.`,
		indicators: [
			indicator({
				id: `ind-generic-${slug}`,
				name: value,
				pattern: `[domain-name:value = '${value}']`,
				main_observable_type: "Domain-Name",
				score: 30,
				confidence: 25
			})
		],
		indicators_count: 3, // "+2 more in OpenCTI"
		reports: [
			report(`rep-generic-${slug}-1`, `Infrastructure report mentioning ${value}`, daysAgo(6)),
			report(`rep-generic-${slug}-2`, "Weekly TI digest 2026-W37", daysAgo(9))
		],
		reports_count: 4 // "+2 more in OpenCTI"
	})
}

const LOOKUPS: Record<string, OpenCTIObservableLookup> = {
	"45.155.205.233": { value: "45.155.205.233", found: true, total: 1, observables: [OBS_IPV4] },
	"sdk.netnut.io": { value: "sdk.netnut.io", found: true, total: 5, observables: [OBS_DOMAIN, OBS_HOSTNAME] },
	[SHA256]: { value: SHA256, found: true, total: 1, observables: [OBS_FILE] },
	[SHA1]: { value: SHA1, found: true, total: 1, observables: [OBS_FILE] },
	[MD5]: { value: MD5, found: true, total: 1, observables: [OBS_FILE] },
	"http://185.220.101.47/gate.php": {
		value: "http://185.220.101.47/gate.php",
		found: true,
		total: 1,
		observables: [OBS_URL]
	},
	"invoice@dhl-express-delivery.com": {
		value: "invoice@dhl-express-delivery.com",
		found: true,
		total: 1,
		observables: [OBS_EMAIL]
	},
	long: { value: OBS_LONG.value!, found: true, total: 1, observables: [OBS_LONG] },
	"1.2.3.4": { value: "1.2.3.4", found: false, total: 0, observables: [] }
}

// ---------------------------------------------------------------------------
// entities (detail drawer)
// ---------------------------------------------------------------------------

function entityFromIndicator(ind: OpenCTIIndicator): OpenCTIEntity {
	return {
		id: ind.id,
		standard_id: ind.standard_id,
		entity_type: "Indicator",
		parent_types: ["Basic-Object", "Stix-Object", "Stix-Core-Object", "Stix-Domain-Object"],
		name: ind.name,
		description:
			ind.description ??
			(ind.pattern
				? `Pattern (${ind.pattern_type}):\n${ind.pattern}\n\nValid from ${ind.valid_from ?? "—"} to ${ind.valid_until ?? "no expiry"}.`
				: null),
		confidence: ind.confidence,
		score: ind.score,
		created_at: ind.created_at,
		updated_at: ind.updated_at,
		created_by: ind.created_by,
		labels: ind.labels,
		markings: ind.markings,
		external_references: [
			{
				source_name: "abuse.ch ThreatFox",
				url: `https://threatfox.abuse.ch/browse.php?search=ioc%3A${encodeURIComponent(ind.name ?? "")}`,
				external_id: `ioc:${(ind.score ?? 0) * 137 + 100000}`,
				description: "ThreatFox IOC page"
			},
			{
				source_name: "VirusTotal",
				url: `https://www.virustotal.com/gui/search/${encodeURIComponent(ind.name ?? "")}`,
				external_id: null,
				description: null
			},
			{
				source_name: "mitre-attack",
				url: "https://attack.mitre.org/techniques/T1071/001/",
				external_id: "T1071.001",
				description: "Application Layer Protocol: Web Protocols"
			},
			{
				source_name: null,
				url: null,
				external_id: "INTERNAL-2026-0917",
				description: "Reference with no source name and no URL"
			}
		]
	}
}

const ENTITIES: Record<string, OpenCTIEntity> = Object.fromEntries(
	MOCK_INDICATORS.filter(i => i.name !== "deleted-entity.example").map(i => [i.id, entityFromIndicator(i)])
)

// Malware entity, reachable from the detail drawer by id (not from the table).
ENTITIES["mal-0001"] = {
	id: "mal-0001",
	standard_id: "malware--8b2c6a1e-2f9e-4a4b-9a7e-2c0f3a1d5e77",
	entity_type: "Malware",
	parent_types: ["Basic-Object", "Stix-Object", "Stix-Core-Object", "Stix-Domain-Object"],
	name: "LockBit 3.0",
	description:
		"LockBit 3.0, also known as LockBit Black, is a ransomware-as-a-service (RaaS) operation active since June 2022. Affiliates gain initial access via RDP, phishing and exploited VPN appliances, then use Cobalt Strike for lateral movement before deploying the encryptor.\n\nThe encryptor deletes Volume Shadow Copies, clears Windows event logs and disables Windows Defender.",
	confidence: 100,
	score: null,
	created_at: daysAgo(900),
	updated_at: daysAgo(1),
	created_by: "Mandiant",
	labels: [LABELS[7], LABELS[6]],
	markings: ["TLP:CLEAR"],
	external_references: [
		{
			source_name: "mitre-attack",
			url: "https://attack.mitre.org/software/S1091/",
			external_id: "S1091",
			description: null
		},
		{
			source_name: "CISA",
			url: "https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-165a",
			external_id: "AA23-165A",
			description: "#StopRansomware: LockBit 3.0"
		}
	]
}

// ---------------------------------------------------------------------------
// about / availability
// ---------------------------------------------------------------------------

const ABOUT: OpenCTIAbout = {
	version: "6.4.8",
	dependencies: [
		{ name: "elasticsearch", version: "8.15.2" },
		{ name: "redis", version: "7.4.1" },
		{ name: "rabbitmq", version: "3.13.7" },
		{ name: "minio", version: "RELEASE.2025-04-22" }
	],
	user_name: "copilot-connector",
	user_email: "copilot@socfortress.example"
}

const AVAILABILITY: OpenCTIAvailability = {
	configured: true,
	verified: true,
	platform_url: MOCK_PLATFORM_URL
}

// ---------------------------------------------------------------------------
// the mock API — drop-in for `Api.opencti`
// ---------------------------------------------------------------------------

function applyQuery(query: OpenCTIIndicatorsQuery): { indicators: OpenCTIIndicator[]; page_info: OpenCTIPageInfo } {
	const search = (query.search ?? "").trim().toLowerCase()
	if (search === "error") throw new Error("mock-error")

	let rows = MOCK_INDICATORS
	if (search === "empty") {
		rows = []
	} else if (search === "slow" || search === "nocount") {
		// keep the full set; the effect is applied in getIndicators()
	} else if (search) {
		// OpenCTI matches whole tokens; approximate that with token containment.
		const tokens = search.split(/\s+/)
		rows = rows.filter(r => {
			const hay =
				`${r.name ?? ""} ${r.pattern ?? ""} ${r.description ?? ""} ${r.labels.map(l => l.value).join(" ")} ${r.created_by ?? ""}`.toLowerCase()
			return tokens.every(t => hay.includes(t))
		})
	}
	if (query.main_observable_type) rows = rows.filter(r => r.main_observable_type === query.main_observable_type)
	if (query.min_score !== undefined && query.min_score !== null)
		rows = rows.filter(r => r.score !== null && r.score >= query.min_score!)

	const first = query.first ?? 25
	const offset = query.after ? Number.parseInt(query.after.replace("cursor:", ""), 10) || 0 : 0
	const page = rows.slice(offset, offset + first)
	const end = offset + page.length

	return {
		indicators: page,
		page_info: {
			global_count: rows.length,
			has_next_page: end < rows.length,
			end_cursor: end < rows.length ? `cursor:${end}` : null
		}
	}
}

export const mockOpenCTI = {
	getAvailability() {
		return wait(AVAILABILITY, 150)
	},
	getAbout(_signal?: AbortSignal) {
		return wait({ about: ABOUT })
	},
	lookupObservable(value: string, _signal?: AbortSignal) {
		const key = value.trim()
		const lower = key.toLowerCase()
		if (lower === "error") return fail("OpenCTI returned AUTH_REQUIRED: the connector token was revoked.")
		if (lower === "slow") return wait(LOOKUPS["45.155.205.233"]!, 4000)
		const hit = LOOKUPS[key] ?? LOOKUPS[lower]
		if (hit) return wait(hit)
		return wait<OpenCTIObservableLookup>({
			value: key,
			found: true,
			total: 1,
			observables: [genericObservable(key)]
		})
	},
	lookupObservables(values: string[]) {
		return wait({
			results: values.map(v => {
				const hit = LOOKUPS[v] ?? LOOKUPS[v.toLowerCase()]
				return { value: v, found: !!hit && hit.found, observables: hit?.observables ?? [] }
			}),
			truncated: values.length > 50
		})
	},
	getIndicators(query: OpenCTIIndicatorsQuery = {}, _signal?: AbortSignal) {
		const search = (query.search ?? "").trim().toLowerCase()
		try {
			const page = applyQuery(query)
			if (search === "nocount") page.page_info.global_count = null
			return wait(page, search === "slow" ? 4000 : query.after ? 900 : DEFAULT_DELAY_MS)
		} catch {
			return fail("OpenCTI GraphQL validation failed: Unknown argument 'search' on field 'indicators'.")
		}
	},
	getEntity(entityId: string, _signal?: AbortSignal) {
		const entity = ENTITIES[entityId]
		if (!entity) return fail(`Entity ${entityId} not found in OpenCTI.`)
		return wait({ entity }, 700)
	}
}

export default mockOpenCTI
