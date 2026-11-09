import type { KnowledgeItem } from "@/types/customer-knowledge"
import { describe, expect, it } from "vitest"
import { COUNTRY_CODES, COUNTRY_OPTIONS, countryName } from "../countries"
import {
	ACCOUNT_ROLE_OPTIONS,
	accountIdProblem,
	accountProblem,
	ALIASES_MAX,
	buildBody,
	cidrProblem,
	closedWeek,
	countriesProblem,
	DOMAIN_USE_OPTIONS,
	domainProblem,
	emptyForm,
	EXPECTED_MAX_DAYS,
	EXPECTED_OPTIONS,
	expiryProblem,
	factView,
	formFromItem,
	fromCalendar,
	fullWeek,
	groupFacts,
	hostNameProblem,
	hostProblem,
	hoursLines,
	identifierProblem,
	KIND_WORDS,
	KINDS,
	knowledgeRules,
	lastChanged,
	listProblem,
	NOTE_MAX,
	noteProblem,
	nowThere,
	openDays,
	ownerProblem,
	PROBLEMS,
	PROVIDER_OPTIONS,
	refusalText,
	ROLE_OPTIONS,
	SINGLE_KINDS,
	startProblem,
	targetProblem,
	tenantIdProblem,
	tenantNameProblem,
	timeZoneProblem,
	USE_OPTIONS,
	weekProblem,
	ZONE_OPTIONS
} from "../knowledge"

const NOW = Date.parse("2026-11-06T12:00:00Z")
const DAY = 86_400_000

const when = (moment: string) => `<${moment}>`

const COMMON = {
	id: 1,
	customer_code: "ACME",
	branch: "network",
	note: null,
	status: "approved",
	source: "soc",
	version: 1,
	expires_at: null,
	expired: false,
	created_at: null,
	updated_at: null,
	updated_by_username: null
}

const ZONE: KnowledgeItem = { ...COMMON, kind: "network_zone", value: { cidr: "10.0.0.0/24", zone: "dmz" } }
const PUBLIC: KnowledgeItem = { ...COMMON, kind: "public_range", value: { cidr: "203.0.113.0/24", use: "hosted" } }
const ASSET: KnowledgeItem = {
	...COMMON,
	kind: "asset_role",
	value: { host: "dc01", role: "domain_controller", crown_jewel: true, owner: "Finance IT" }
}
const EXPECTED: KnowledgeItem = {
	...COMMON,
	kind: "expected_activity",
	value: {
		what: "pentest",
		hosts: ["scan01"],
		source_cidrs: ["10.0.0.5/32"],
		accounts: [],
		starts_at: "2026-11-06T12:00:00+00:00"
	},
	expires_at: "2026-11-20T12:00:00+00:00"
}
const DOMAIN: KnowledgeItem = {
	...COMMON,
	branch: "domains",
	kind: "own_domain",
	value: { domain: "example.com", uses: ["email", "upn"] }
}
const TENANT: KnowledgeItem = {
	...COMMON,
	branch: "domains",
	kind: "identity_tenant",
	value: { provider: "entra", tenant_id: "72f988bf-86f1-41af-91ab-2d7cd011db47", name: "contoso.onmicrosoft.com" }
}
const ACCOUNT: KnowledgeItem = {
	...COMMON,
	branch: "people",
	kind: "account_role",
	value: { account: "CORP\\jsmith", role: "break_glass", aliases: ["jsmith@corp.example"] }
}
const WORKDAY: [string, string][] = [["08:00", "17:00"]]
const BUSINESS: KnowledgeItem = {
	...COMMON,
	branch: "business",
	kind: "business_profile",
	value: {
		time_zone: "America/Denver",
		week: { mon: WORKDAY, tue: WORKDAY, wed: WORKDAY, thu: WORKDAY, fri: WORKDAY, sat: [["09:00", "12:00"]] },
		always_open: false,
		countries: ["US", "CA"]
	}
}

describe("cidrProblem", () => {
	it.each(["10.0.0.0/24", "10.0.0.5", " 10.0.0.0/8 ", "2001:db8::/48", "2001:db8::1"])("takes %s", value => {
		expect(cidrProblem(value)).toBeNull()
	})

	it.each(["", "   ", "10.0.0", "10.0.0.0/33", "10.0.0.0/", "2001:db8::/129", "dc01", "10.0.0.0/24/8"])(
		"refuses %j",
		value => {
			expect(cidrProblem(value)).toBe(PROBLEMS.cidr)
		}
	)

	it.each(["fe80::1%eth0", "fe80::1%25", "fe80::/64%eth0", "10.0.0.1%"])("refuses the scope id in %s", value => {
		expect(cidrProblem(value)).toBe(PROBLEMS.cidr)
	})
})

describe("refusalText", () => {
	it("words a backend refusal as the form's own problems are", () => {
		expect(refusalText("the expiry is in the past.")).toBe("The expiry is in the past.")
		expect(refusalText("Already capitalised.")).toBe("Already capitalised.")
		expect(refusalText("")).toBe("")
	})

	it("reads the same as the form's own text, for the refusals the form can check itself", () => {
		const backend: [string, string][] = [
			["host names can't hold spaces, wildcards, angle brackets or control characters", PROBLEMS.host],
			["account names can't hold wildcards, angle brackets or control characters", PROBLEMS.account],
			["notes, owners and names can't hold angle brackets or control characters", PROBLEMS.text],
			["enter a domain name, such as example.com, without a scheme, path, port or wildcard", PROBLEMS.domain],
			[
				"record the account's name, such as jsmith, CORP\\jsmith or jsmith@corp.com, not a display name",
				PROBLEMS.identifier
			],
			["an Entra tenant id is a GUID, such as 72f988bf-86f1-41af-91ab-2d7cd011db47", PROBLEMS.entraTenant],
			["a Google Workspace customer id starts with C, such as C01b2c3d4", PROBLEMS.googleTenant],
			["enter the tenant's id as the provider shows it", PROBLEMS.tenant],
			["the start can't be more than 90 days ago", PROBLEMS.startTooOld],
			["expected activity can't run for more than 90 days", PROBLEMS.windowTooLong],
			["expected activity can't run for more than 90 days from now", PROBLEMS.expiryTooFar]
		]
		for (const [text, problem] of backend) expect(refusalText(text)).toBe(problem)
	})
})

describe("names", () => {
	const UNSAFE: [string, string][] = [
		["a wildcard", "dc*01"],
		["a percent wildcard", "dc%01"],
		["an angle bracket", "dc<01"],
		["a closing angle bracket", "dc>01"],
		["a control character", "dc\u000701"],
		["a C1 control character", "dc\u008501"],
		["a zero-width space", "dc\u200B01"],
		["a right-to-left override", "dc\u202E01"],
		["a line separator", "dc\u202801"],
		["a paragraph separator", "dc\u202901"],
		["a private use character", "dc\uE00001"],
		["a lone surrogate", "dc\uD80001"]
	]

	it.each(UNSAFE)("refuses %s in a host", (_what, value) => {
		expect(hostNameProblem(value)).toBe(PROBLEMS.host)
	})

	it.each(UNSAFE)("refuses %s in an account", (_what, value) => {
		expect(accountProblem(value)).toBe(PROBLEMS.account)
	})

	it("takes a host name, trimmed, and no whitespace at all", () => {
		expect(hostNameProblem("dc01.corp.example")).toBeNull()
		expect(hostNameProblem(" dc01 ")).toBeNull()
		expect(hostNameProblem("dc 01")).toBe(PROBLEMS.host)
		expect(hostNameProblem("dc\t01")).toBe(PROBLEMS.host)
		expect(hostNameProblem("dc\u00A001")).toBe(PROBLEMS.host)
		expect(hostNameProblem("x".repeat(256))).toContain("255")
		expect(hostNameProblem(` ${"x".repeat(255)} `)).toBeNull()
	})

	it("takes an account name with ordinary spaces, but no other whitespace", () => {
		expect(accountProblem("CORP\\svc-scan")).toBeNull()
		expect(accountProblem(" svc ")).toBeNull()
		expect(accountProblem("NT AUTHORITY\\SYSTEM")).toBeNull()
		expect(hostNameProblem("NT AUTHORITY\\SYSTEM")).toBe(PROBLEMS.host)
		expect(accountProblem("svc\tscan")).toBe(PROBLEMS.account)
		expect(accountProblem("svc\nscan")).toBe(PROBLEMS.account)
		expect(accountProblem("svc\u00A0scan")).toBe(PROBLEMS.account)
		expect(accountProblem("svc\u3000scan")).toBe(PROBLEMS.account)
		expect(accountProblem("x".repeat(256))).toContain("255")
	})

	it("needs the host of an asset role, but leaves its owner free to hold spaces", () => {
		expect(hostProblem("  ")).toBe("Enter the host's name")
		expect(hostProblem("dc 01")).toBe(PROBLEMS.host)
		expect(hostProblem("dc01")).toBeNull()
		expect(ownerProblem("Finance IT")).toBeNull()
		expect(ownerProblem("")).toBeNull()
		expect(ownerProblem("x".repeat(256))).toContain("255")
	})
})

describe("free text", () => {
	it("measures what is sent, without the spaces around it", () => {
		expect(noteProblem("x".repeat(NOTE_MAX))).toBeNull()
		expect(noteProblem(`  ${"x".repeat(NOTE_MAX)}  `)).toBeNull()
		expect(noteProblem("x".repeat(NOTE_MAX + 1))).toContain("200")
	})

	it("reads a note as the one line the backend stores, so a newline is fine", () => {
		expect(noteProblem("first line\nsecond line")).toBeNull()
		expect(noteProblem("first line\r\n\tsecond line\n")).toBeNull()
		expect(ownerProblem("Finance\nIT")).toBeNull()
	})

	it.each(["<b>", "a > b", "esc\u001B[0m", "zero\u200Bwidth", "rtl\u202Eoverride"])("refuses %j", value => {
		expect(noteProblem(value)).toBe(PROBLEMS.text)
		expect(ownerProblem(value)).toBe(PROBLEMS.text)
	})

	it("says the length first, as the backend does", () => {
		expect(noteProblem("<".repeat(NOTE_MAX + 1))).toContain("200")
		expect(ownerProblem("<".repeat(256))).toContain("255")
	})
})

describe("listProblem", () => {
	it("skips blank rows and names the first bad one", () => {
		expect(listProblem(["", "  ", "10.0.0.1"], cidrProblem)).toBeNull()
		expect(listProblem(["10.0.0.1", "nope", "worse"], cidrProblem)).toBe(`nope: ${PROBLEMS.cidr}`)
	})
})

describe("targetProblem", () => {
	const form = emptyForm("expected_activity")

	it("needs a host or a source range, and blank rows are neither", () => {
		expect(targetProblem(form)).toBe(PROBLEMS.needsTarget)
		expect(targetProblem({ ...form, hosts: ["", " "], accounts: ["svc"] })).toBe(PROBLEMS.needsTarget)
		expect(targetProblem({ ...form, hosts: ["scan01"] })).toBeNull()
		expect(targetProblem({ ...form, sourceCidrs: ["10.0.0.5"] })).toBeNull()
	})
})

describe("startProblem", () => {
	const OLDEST = NOW - EXPECTED_MAX_DAYS * DAY

	it("needs a start, and a past one is fine: the work may have begun", () => {
		expect(startProblem(null, NOW)).toContain("start")
		expect(startProblem(NOW - DAY, NOW)).toBeNull()
		expect(startProblem(NOW + DAY, NOW)).toBeNull()
	})

	it("refuses a start more than 90 days ago", () => {
		expect(startProblem(OLDEST, NOW)).toBeNull()
		expect(startProblem(OLDEST - 1, NOW)).toBe(PROBLEMS.startTooOld)
	})

	it("lets an edit keep the stored start, however old, but not move to another old one", () => {
		expect(startProblem(OLDEST - DAY, NOW, OLDEST - DAY)).toBeNull()
		expect(startProblem(OLDEST - 2 * DAY, NOW, OLDEST - DAY)).toBe(PROBLEMS.startTooOld)
		expect(startProblem(null, NOW, OLDEST - DAY)).toContain("start")
	})
})

describe("expiryProblem", () => {
	it("leaves the expiry optional on the other kinds, but never in the past", () => {
		for (const kind of ["network_zone", "public_range", "asset_role"] as const) {
			expect(expiryProblem(emptyForm(kind), NOW)).toBeNull()
			expect(expiryProblem({ ...emptyForm(kind), expiresAt: NOW + 400 * DAY }, NOW)).toBeNull()
			expect(expiryProblem({ ...emptyForm(kind), expiresAt: NOW }, NOW)).toBe(PROBLEMS.expiryPast)
		}
	})

	it("needs one on expected activity, in the next 90 days and after the start", () => {
		const form = { ...emptyForm("expected_activity"), startsAt: NOW }
		expect(expiryProblem(form, NOW)).toBe(PROBLEMS.needsExpiry)
		expect(expiryProblem({ ...form, expiresAt: NOW - 1 }, NOW)).toBe(PROBLEMS.expiryPast)
		expect(expiryProblem({ ...form, expiresAt: NOW + EXPECTED_MAX_DAYS * DAY }, NOW)).toBeNull()
		expect(expiryProblem({ ...form, expiresAt: NOW + EXPECTED_MAX_DAYS * DAY + 1 }, NOW)).toBe(
			PROBLEMS.expiryTooFar
		)
		expect(expiryProblem({ ...form, startsAt: NOW + 2 * DAY, expiresAt: NOW + DAY }, NOW)).toBe(
			PROBLEMS.expiryBeforeStart
		)
		expect(expiryProblem({ ...form, startsAt: NOW + DAY, expiresAt: NOW + DAY }, NOW)).toBe(
			PROBLEMS.expiryBeforeStart
		)
	})

	it("lets an edit keep an expired expiry, but not move it to another past time", () => {
		const form = formFromItem({ ...ZONE, expired: true, expires_at: "2026-01-01T00:00:00+00:00" })
		const kept = form.expiresAt
		expect(expiryProblem(form, NOW, kept)).toBeNull()
		expect(expiryProblem(form, NOW)).toBe(PROBLEMS.expiryPast)
		expect(expiryProblem({ ...form, expiresAt: (kept as number) + DAY }, NOW, kept)).toBe(PROBLEMS.expiryPast)
	})

	it("lets an edit keep an expiry that is now too far off, but not move it further", () => {
		const form = { ...emptyForm("expected_activity"), startsAt: NOW + 50 * DAY, expiresAt: NOW + 100 * DAY }
		expect(expiryProblem(form, NOW, form.expiresAt)).toBeNull()
		expect(expiryProblem(form, NOW)).toBe(PROBLEMS.expiryTooFar)
		expect(expiryProblem({ ...form, expiresAt: NOW + 101 * DAY }, NOW, form.expiresAt)).toBe(PROBLEMS.expiryTooFar)
	})

	it("refuses a window over 90 days, even when both times are kept", () => {
		const form = { ...emptyForm("expected_activity"), startsAt: NOW - 10 * DAY, expiresAt: NOW + 80 * DAY }
		expect(expiryProblem(form, NOW)).toBeNull()
		const long = { ...form, expiresAt: form.expiresAt + 1 }
		expect(expiryProblem(long, NOW)).toBe(PROBLEMS.windowTooLong)
		expect(expiryProblem(long, NOW, long.expiresAt)).toBe(PROBLEMS.windowTooLong)
	})

	it("always needs an expiry on expected activity, after its start", () => {
		const form = { ...emptyForm("expected_activity"), startsAt: NOW - 2 * DAY, expiresAt: NOW - 3 * DAY }
		expect(expiryProblem(form, NOW, form.expiresAt)).toBe(PROBLEMS.expiryBeforeStart)
		expect(expiryProblem({ ...form, expiresAt: null }, NOW, form.expiresAt)).toBe(PROBLEMS.needsExpiry)
	})

	it("doesn't apply the expected activity limits to the other kinds, even with a kept expiry", () => {
		const form = { ...emptyForm("network_zone"), expiresAt: NOW + 400 * DAY }
		expect(expiryProblem(form, NOW, form.expiresAt)).toBeNull()
		expect(expiryProblem({ ...form, expiresAt: null }, NOW, form.expiresAt)).toBeNull()
	})
})

describe("knowledgeRules", () => {
	type Validator = (rule: never, value: unknown) => true | Error
	const validate = (rule: unknown, value: unknown) => (rule as { validator: Validator }).validator({} as never, value)

	it("turns a problem into an Error, and marks the fields that can't be left out", () => {
		const rules = knowledgeRules(emptyForm("network_zone"))
		expect(validate(rules.cidr, "nope")).toEqual(new Error(PROBLEMS.cidr))
		expect(validate(rules.cidr, "10.0.0.0/24")).toBe(true)
		expect(rules.cidr).toMatchObject({ required: true })
		expect(rules.zone).toMatchObject({ required: true })
		expect(rules.note).toMatchObject({ required: false })
		expect(rules.expiresAt).toMatchObject({ required: false })
	})

	it("asks expected activity for a target on the hosts field, whichever list holds it", () => {
		const form = emptyForm("expected_activity")
		const rules = knowledgeRules(form)
		expect(rules.expiresAt).toMatchObject({ required: true })
		expect(validate(rules.hosts, [])).toEqual(new Error(PROBLEMS.needsTarget))
		form.sourceCidrs = ["10.0.0.5"]
		expect(validate(rules.hosts, [])).toBe(true)
		expect(validate(rules.hosts, ["dc 01"])).toEqual(new Error(`dc 01: ${PROBLEMS.host}`))
		expect(validate(rules.sourceCidrs, ["nope"])).toEqual(new Error(`nope: ${PROBLEMS.cidr}`))
	})

	it("holds an account to the account's rule, not the host's", () => {
		const rules = knowledgeRules(emptyForm("expected_activity"))
		expect(validate(rules.accounts, ["NT AUTHORITY\\SYSTEM"])).toBe(true)
		expect(validate(rules.accounts, ["svc*"])).toEqual(new Error(`svc*: ${PROBLEMS.account}`))
	})

	describe("on an edit", () => {
		const opened = (): KnowledgeItem =>
			({
				...EXPECTED,
				expired: true,
				value: { ...EXPECTED.value, starts_at: new Date(Date.now() - 200 * DAY).toISOString() },
				expires_at: new Date(Date.now() - 150 * DAY).toISOString()
			}) as KnowledgeItem

		it("lets a note change on a fact that has expired, leaving both times alone", () => {
			const item = opened()
			const form = formFromItem(item)
			const rules = knowledgeRules({ ...form, note: "a new note" }, formFromItem(item))
			expect(validate(rules.startsAt, form.startsAt)).toBe(true)
			expect(validate(rules.expiresAt, form.expiresAt)).toBe(true)
		})

		it("refuses old times that aren't the stored ones", () => {
			const item = opened()
			const form = formFromItem(item)
			const moved = { ...form, expiresAt: (form.expiresAt as number) + 1000 }
			const rules = knowledgeRules(moved, formFromItem(item))
			expect(validate(rules.startsAt, (form.startsAt as number) + 1000)).toEqual(new Error(PROBLEMS.startTooOld))
			expect(validate(rules.expiresAt, moved.expiresAt)).toEqual(new Error(PROBLEMS.expiryPast))
		})

		it("holds a new fact to the rules whole", () => {
			const form = formFromItem(opened())
			const rules = knowledgeRules(form)
			expect(validate(rules.startsAt, form.startsAt)).toEqual(new Error(PROBLEMS.startTooOld))
			expect(validate(rules.expiresAt, form.expiresAt)).toEqual(new Error(PROBLEMS.expiryPast))
		})
	})
})

describe("buildBody", () => {
	it("sends exactly what each kind's model takes, trimmed", () => {
		expect(buildBody({ ...emptyForm("network_zone"), cidr: " 10.0.0.0/24 ", zone: "dmz", note: "  " })).toEqual({
			kind: "network_zone",
			value: { cidr: "10.0.0.0/24", zone: "dmz" },
			note: null,
			expires_at: null
		})
		expect(
			buildBody({ ...emptyForm("public_range"), cidr: "203.0.113.0/24", use: "egress", note: " NAT " })
		).toEqual({
			kind: "public_range",
			value: { cidr: "203.0.113.0/24", use: "egress" },
			note: "NAT",
			expires_at: null
		})
	})

	it("sends a blank owner as null", () => {
		const form = { ...emptyForm("asset_role"), host: " dc01 ", role: "backup" as const, owner: "  " }
		expect(buildBody(form)).toEqual({
			kind: "asset_role",
			value: { host: "dc01", role: "backup", crown_jewel: false, owner: null },
			note: null,
			expires_at: null
		})
	})

	it("drops blank rows and sends times in UTC", () => {
		const form = {
			...emptyForm("expected_activity"),
			what: "scanner" as const,
			hosts: [" scan01 ", ""],
			sourceCidrs: ["  "],
			accounts: ["svc"],
			startsAt: NOW,
			expiresAt: NOW + DAY
		}
		expect(buildBody(form)).toEqual({
			kind: "expected_activity",
			value: {
				what: "scanner",
				hosts: ["scan01"],
				source_cidrs: [],
				accounts: ["svc"],
				starts_at: "2026-11-06T12:00:00.000Z"
			},
			note: null,
			expires_at: "2026-11-07T12:00:00.000Z"
		})
	})

	it("sends a fact back as it came, so an edit changes only what the analyst changed", () => {
		for (const item of [ZONE, PUBLIC, ASSET, EXPECTED, DOMAIN, TENANT, ACCOUNT]) {
			const body = buildBody(formFromItem(item))
			expect(body.kind).toBe(item.kind)
			expect(Object.keys(body.value).sort()).toEqual(Object.keys(item.value).sort())
		}
		expect(buildBody(formFromItem(ASSET)).value).toEqual(ASSET.value)
		const body = buildBody(formFromItem(EXPECTED))
		expect(Date.parse(body.expires_at ?? "")).toBe(Date.parse(EXPECTED.expires_at ?? ""))
		expect(body.value).toMatchObject({ what: "pentest", hosts: ["scan01"], source_cidrs: ["10.0.0.5/32"] })
	})

	it("clears a note or an expiry by sending null", () => {
		const form = formFromItem({ ...ZONE, note: "old", expires_at: "2030-01-01T00:00:00+00:00" })
		expect(buildBody({ ...form, note: "", expiresAt: null })).toMatchObject({ note: null, expires_at: null })
	})
})

describe("formFromItem", () => {
	it("copies the lists, so editing the form leaves the fact alone", () => {
		const form = formFromItem(EXPECTED)
		form.hosts.push("other")
		expect(EXPECTED.kind === "expected_activity" && EXPECTED.value.hosts).toEqual(["scan01"])
	})
})

describe("factView", () => {
	it("shows each kind's key values, in words", () => {
		expect(factView(ZONE, when)).toEqual({
			headline: "10.0.0.0/24",
			crownJewel: false,
			details: [{ label: "Zone", values: ["DMZ"] }]
		})
		expect(factView(PUBLIC, when).details).toEqual([{ label: "Use", values: ["Hosted services"] }])
		expect(factView(ASSET, when)).toEqual({
			headline: "dc01",
			crownJewel: true,
			details: [
				{ label: "Role", values: ["Domain controller"] },
				{ label: "Owner", values: ["Finance IT"] }
			]
		})
		expect(factView(EXPECTED, when)).toEqual({
			headline: "Pentest",
			crownJewel: false,
			details: [
				{ label: "Hosts", values: ["scan01"] },
				{ label: "Source ranges", values: ["10.0.0.5/32"] },
				{ label: "Starts", values: ["<2026-11-06T12:00:00+00:00>"] },
				{ label: "Expires", values: ["<2026-11-20T12:00:00+00:00>"] }
			]
		})
	})

	it("reads a value this page doesn't know yet as itself", () => {
		const newer = { ...ZONE, value: { cidr: "10.0.0.0/24", zone: "iot" } } as unknown as KnowledgeItem
		expect(factView(newer, when).details).toEqual([{ label: "Zone", values: ["iot"] }])
	})
})

describe("lastChanged", () => {
	it("says who and when, with what it has", () => {
		const at = "2026-11-06T12:00:00+00:00"
		expect(lastChanged({ ...ZONE, updated_by_username: "ana", updated_at: at }, when)).toBe(
			`Last changed by ana, <${at}>`
		)
		expect(lastChanged({ ...ZONE, updated_by_username: "ana" }, when)).toBe("Last changed by ana")
		expect(lastChanged({ ...ZONE, updated_at: at }, when)).toBe(`Last changed <${at}>`)
		expect(lastChanged(ZONE, when)).toBeNull()
	})
})

describe("groupFacts", () => {
	it("gives every block in order, each with its facts, empty or not", () => {
		const groups = groupFacts([EXPECTED, ZONE, { ...ZONE, id: 2 }, ACCOUNT])
		expect(groups.map(group => group.kind)).toEqual(KINDS)
		expect(groups.map(group => group.title)).toEqual([
			"Business context",
			"Network zones",
			"Public ranges",
			"Asset roles",
			"Expected activity",
			"Domains",
			"Identity tenants",
			"Accounts"
		])
		expect(groups.map(group => group.facts.length)).toEqual([0, 2, 0, 0, 1, 0, 0, 1])
		expect(groups.every(group => group.canAdd)).toBe(true)
	})

	it("leaves out a kind this page doesn't know yet", () => {
		const newer = { ...ZONE, kind: "vendor_contact" } as unknown as KnowledgeItem
		expect(groupFacts([newer]).every(group => group.facts.length === 0)).toBe(true)
	})
})

describe("the words", () => {
	it("explain every kind", () => {
		for (const kind of KINDS) expect(KIND_WORDS[kind].about.length).toBeGreaterThan(0)
	})

	it("offer the values the backend's models take", () => {
		const values = (list: { value: string }[]) => list.map(option => option.value)
		expect(values(ZONE_OPTIONS)).toEqual([
			"server",
			"workstation",
			"dmz",
			"guest",
			"ot",
			"vpn",
			"cloud",
			"management",
			"other"
		])
		expect(values(USE_OPTIONS)).toEqual(["egress", "hosted", "other"])
		expect(values(ROLE_OPTIONS)).toEqual([
			"domain_controller",
			"file_server",
			"database",
			"web_server",
			"mail_server",
			"backup",
			"hypervisor",
			"jump_host",
			"security_tool",
			"workstation",
			"other"
		])
		expect(values(EXPECTED_OPTIONS)).toEqual(["scanner", "rmm", "pentest", "change_window", "other"])
	})
})

// ── plan K1-7: domains, tenants and accounts ──────────────────────────────────

describe("domainProblem", () => {
	it.each([
		"example.com",
		" Mail.Example.COM ",
		"example.com.",
		"bücher.example",
		"xn--bcher-kva.example",
		"example.co.uk"
	])("takes %s", value => {
		expect(domainProblem(value)).toBeNull()
	})

	it.each([
		"com",
		"*.example.com",
		"https://example.com",
		"example.com/login",
		"example.com:443",
		"user@example.com",
		"exa mple.com",
		"-bad.example.com",
		"a..example.com",
		"example.123",
		"10.0.0.1",
		"2001:db8::1",
		`${"x".repeat(64)}.com`,
		"e\u200Bxample.com",
		"example.com<",
		"example_name.com"
	])("refuses %j", value => {
		expect(domainProblem(value)).toBe(PROBLEMS.domain)
	})

	it("asks for a domain when there is none", () => {
		expect(domainProblem("  ")).toBe("Enter the domain")
	})
})

describe("tenantIdProblem", () => {
	it("takes each provider's form", () => {
		expect(tenantIdProblem("entra", "72F988BF-86F1-41AF-91AB-2D7CD011DB47")).toBeNull()
		expect(tenantIdProblem("entra", "{72f988bf-86f1-41af-91ab-2d7cd011db47}")).toBeNull()
		expect(tenantIdProblem("google", "C01b2c3d4")).toBeNull()
		expect(tenantIdProblem("other", "tenant.example:42")).toBeNull()
	})

	it("refuses another form, with the provider's own words", () => {
		expect(tenantIdProblem("entra", "contoso.onmicrosoft.com")).toBe(PROBLEMS.entraTenant)
		expect(tenantIdProblem("google", "x123456")).toBe(PROBLEMS.googleTenant)
		expect(tenantIdProblem("other", "two words")).toBe(PROBLEMS.tenant)
		expect(tenantIdProblem(null, "<tenant>")).toBe(PROBLEMS.tenant)
		expect(tenantIdProblem("entra", " ")).toBe("Enter the tenant's id")
	})

	it("holds a tenant's name to the free-text rules", () => {
		expect(tenantNameProblem("Contoso Ltd")).toBeNull()
		expect(tenantNameProblem("</customer_context>")).toBe(PROBLEMS.text)
		expect(tenantNameProblem("x".repeat(256))).toContain("255")
	})
})

describe("identifierProblem", () => {
	it.each(["jsmith", "CORP\\jsmith", "NT AUTHORITY\\SYSTEM", "jsmith@corp.example", "svc-backup$"])(
		"takes %s",
		value => {
			expect(identifierProblem(value)).toBeNull()
		}
	)

	it.each([
		"Jane Smith",
		"CORP\\Jane Smith",
		"\\jsmith",
		"CORP\\",
		"CORP\\a\\b",
		"a@b@c",
		"@corp.example",
		"jsmith@",
		"j smith@corp.example"
	])("refuses the display name or broken form %j", value => {
		expect(identifierProblem(value)).toBe(PROBLEMS.identifier)
	})

	it("keeps the account-name rules first", () => {
		expect(identifierProblem("svc*")).toBe(PROBLEMS.account)
		expect(identifierProblem("svc\u200B")).toBe(PROBLEMS.account)
	})

	it("asks for an account when there is none", () => {
		expect(accountIdProblem(" ")).toBe("Enter the account's name")
	})
})

describe("the K1-7 forms", () => {
	it("send exactly what each kind's model takes, trimmed", () => {
		expect(buildBody({ ...emptyForm("own_domain"), domain: " example.com ", uses: ["web", "email"] })).toEqual({
			kind: "own_domain",
			value: { domain: "example.com", uses: ["web", "email"] },
			note: null,
			expires_at: null
		})
		expect(
			buildBody({
				...emptyForm("identity_tenant"),
				provider: "google",
				tenantId: " C01b2c3d4 ",
				tenantName: "  "
			})
		).toEqual({
			kind: "identity_tenant",
			value: { provider: "google", tenant_id: "C01b2c3d4", name: null },
			note: null,
			expires_at: null
		})
		expect(
			buildBody({
				...emptyForm("account_role"),
				account: " jsmith ",
				accountRole: "vip",
				aliases: [" j.smith ", ""]
			})
		).toEqual({
			kind: "account_role",
			value: { account: "jsmith", role: "vip", aliases: ["j.smith"] },
			note: null,
			expires_at: null
		})
	})

	it("send a fact back as it came", () => {
		for (const item of [DOMAIN, TENANT, ACCOUNT]) expect(buildBody(formFromItem(item)).value).toEqual(item.value)
	})

	it("copy the lists, so editing the form leaves the fact alone", () => {
		const form = formFromItem(ACCOUNT)
		form.aliases.push("other")
		form.uses.push("web")
		expect(ACCOUNT.kind === "account_role" && ACCOUNT.value.aliases).toEqual(["jsmith@corp.example"])
		const domain = formFromItem(DOMAIN)
		domain.uses.push("web")
		expect(DOMAIN.kind === "own_domain" && DOMAIN.value.uses).toEqual(["email", "upn"])
	})

	it("check the fields their kind shows", async () => {
		const rules = knowledgeRules({ ...emptyForm("identity_tenant"), provider: "entra" })
		const check = (field: string, value: unknown) =>
			(rules[field] as { validator: (rule: unknown, value: unknown) => true | Error }).validator({}, value)
		expect(check("tenantId", "not-a-guid")).toEqual(new Error(PROBLEMS.entraTenant))
		expect(check("tenantId", "72f988bf-86f1-41af-91ab-2d7cd011db47")).toBe(true)
		expect(check("uses", [])).toEqual(new Error("Pick at least one use"))
		expect(check("domain", "gmail.com")).toBe(true) // the backend's refusal: a public mail provider
		expect(check("account", "Jane Smith")).toEqual(new Error(PROBLEMS.identifier))
		expect(check("aliases", ["ok", "Jane Smith"])).toEqual(new Error(`Jane Smith: ${PROBLEMS.identifier}`))
	})

	it("show each kind in words", () => {
		expect(factView(DOMAIN, when)).toEqual({
			headline: "example.com",
			crownJewel: false,
			details: [{ label: "Used for", values: ["Email", "UPN suffix"] }]
		})
		expect(factView(TENANT, when)).toEqual({
			headline: "contoso.onmicrosoft.com",
			crownJewel: false,
			details: [
				{ label: "Provider", values: ["Microsoft Entra (Microsoft 365)"] },
				{ label: "Tenant id", values: ["72f988bf-86f1-41af-91ab-2d7cd011db47"] }
			]
		})
		expect(factView({ ...TENANT, value: { ...TENANT.value, name: null } } as KnowledgeItem, when).headline).toBe(
			"72f988bf-86f1-41af-91ab-2d7cd011db47"
		)
		expect(factView(ACCOUNT, when)).toEqual({
			headline: "CORP\\jsmith",
			crownJewel: false,
			details: [
				{ label: "Role", values: ["Break-glass account"] },
				{ label: "Also known as", values: ["jsmith@corp.example"] }
			]
		})
	})

	it("offer the values the backend's models take", () => {
		const values = (list: { value: string }[]) => list.map(option => option.value)
		expect(values(DOMAIN_USE_OPTIONS)).toEqual(["email", "web", "ad", "upn", "other"])
		expect(values(PROVIDER_OPTIONS)).toEqual(["entra", "google", "other"])
		expect(values(ACCOUNT_ROLE_OPTIONS)).toEqual([
			"vip",
			"executive",
			"admin",
			"service",
			"break_glass",
			"shared",
			"other"
		])
		expect(ALIASES_MAX).toBe(10)
	})
})

describe("the business profile (K1-8)", () => {
	it("is a kind a customer has one of: Add goes once it's recorded", () => {
		expect(SINGLE_KINDS.has("business_profile")).toBe(true)
		const groups = groupFacts([BUSINESS, ZONE])
		expect(groups.find(group => group.kind === "business_profile")?.canAdd).toBe(false)
		expect(groups.filter(group => group.kind !== "business_profile").every(group => group.canAdd)).toBe(true)
		expect(KINDS[0]).toBe("business_profile")
	})

	it("sends the open days in week order, each with its windows in order", () => {
		const week = closedWeek()
		week.sat = [
			["13:00", "17:00"],
			["09:00", "12:00"]
		]
		week.mon = [["08:00", "17:00"]]
		expect(
			buildBody({ ...emptyForm("business_profile"), timeZone: " America/Denver ", week, countries: ["US"] })
		).toEqual({
			kind: "business_profile",
			value: {
				time_zone: "America/Denver",
				week: {
					mon: [["08:00", "17:00"]],
					sat: [
						["09:00", "12:00"],
						["13:00", "17:00"]
					]
				},
				always_open: false,
				countries: ["US"]
			},
			note: null,
			expires_at: null
		})
		expect(Object.keys(openDays(week))).toEqual(["mon", "sat"])
	})

	it("sends no hours for a customer open around the clock, whatever the editor still holds", () => {
		const form = { ...formFromItem(BUSINESS), alwaysOpen: true }
		expect(buildBody(form).value).toEqual({
			time_zone: "America/Denver",
			week: {},
			always_open: true,
			countries: ["US", "CA"]
		})
	})

	it("sends a profile back as it came, and copies its week", () => {
		expect(buildBody(formFromItem(BUSINESS)).value).toEqual(BUSINESS.value)
		const form = formFromItem(BUSINESS)
		form.week.mon.push(["18:00", "19:00"])
		form.countries.push("GB")
		expect(BUSINESS.kind === "business_profile" && BUSINESS.value.week.mon).toEqual(WORKDAY)
		expect(BUSINESS.kind === "business_profile" && BUSINESS.value.countries).toEqual(["US", "CA"])
		expect(formFromItem(BUSINESS).week.sun).toEqual([])
	})

	it("copies an SLA calendar's zone and week, never its holidays, and leaves the calendar alone", () => {
		const calendar = { timezone: "Europe/Rome", week: { mon: WORKDAY } as Record<string, [string, string][]> }
		const copied = fromCalendar(calendar as never)
		expect(copied.timeZone).toBe("Europe/Rome")
		expect(copied.week).toEqual({ ...fullWeek({}), mon: WORKDAY })
		copied.week.mon[0][1] = "18:00"
		expect(calendar.week.mon).toEqual([["08:00", "17:00"]])
	})

	it("takes an IANA zone by region and city, or UTC", () => {
		for (const zone of ["America/Denver", "UTC", "America/Argentina/Buenos_Aires"])
			expect(timeZoneProblem(zone)).toBeNull()
		for (const zone of ["MST", "EST5EDT", "GMT", "Etc/GMT+7"]) expect(timeZoneProblem(zone)).toBe(PROBLEMS.timeZone)
		expect(timeZoneProblem(null)).toBe("Pick the customer's time zone")
		expect(timeZoneProblem(" ")).toBe("Pick the customer's time zone")
	})

	it("names the first day whose windows are wrong, in the SLA editor's words", () => {
		const week = closedWeek()
		expect(weekProblem(week)).toBeNull()
		week.tue = [["22:00", "06:00"]]
		expect(weekProblem(week)).toBe("Tuesday: a window must start before it ends")
		week.mon = [
			["08:00", "12:00"],
			["11:00", "17:00"]
		]
		expect(weekProblem(week)).toBe("Monday: windows overlap")
		week.mon = Array.from({ length: 7 }, (_, i) => [`0${i}:00`, `0${i}:30`] as [string, string])
		expect(weekProblem(week)).toBe("Monday: keep to 6 windows")
	})

	it("doesn't judge the hours of a customer open around the clock", () => {
		const form = { ...emptyForm("business_profile"), alwaysOpen: true }
		form.week.mon = [["17:00", "08:00"]]
		const rules = knowledgeRules(form)
		const check = (field: string, value: unknown) =>
			(rules[field] as { validator: (rule: unknown, value: unknown) => true | Error }).validator({}, value)
		expect(check("week", form.week)).toBe(true)
		form.alwaysOpen = false
		expect(check("week", form.week)).toEqual(new Error("Monday: a window must start before it ends"))
		expect(check("timeZone", "MST")).toEqual(new Error(PROBLEMS.timeZone))
		expect(check("countries", ["US", "XX"])).toEqual(new Error(PROBLEMS.country))
	})

	it("takes ISO country codes the backend takes", () => {
		expect(countriesProblem(["US", "GB", "XK"])).toBeNull()
		expect(countriesProblem(["USA"])).toBe(PROBLEMS.country)
		expect(countriesProblem(["us"])).toBe(PROBLEMS.country)
		expect(countriesProblem(COUNTRY_CODES.slice(0, 51))).toBe("Keep to 50 countries")
		expect(COUNTRY_CODES).toHaveLength(250)
		expect(new Set(COUNTRY_CODES).size).toBe(250)
		expect(COUNTRY_OPTIONS.find(option => option.value === "US")?.label).toBe("United States (US)")
		expect(countryName("GB")).toBe("United Kingdom")
	})

	it("reads the week in words, days with the same windows together", () => {
		expect(hoursLines(BUSINESS.kind === "business_profile" ? BUSINESS.value.week : {})).toEqual([
			"Mon–Fri 08:00–17:00",
			"Sat 09:00–12:00"
		])
		expect(
			hoursLines({
				mon: WORKDAY,
				wed: WORKDAY,
				sat: [
					["09:00", "12:00"],
					["13:00", "15:00"]
				],
				sun: [
					["09:00", "12:00"],
					["13:00", "15:00"]
				]
			})
		).toEqual(["Mon, Wed 08:00–17:00", "Sat, Sun 09:00–12:00, 13:00–15:00"])
		expect(hoursLines({})).toEqual([])
	})

	it("shows the profile in words", () => {
		expect(factView(BUSINESS, when)).toEqual({
			headline: "America/Denver",
			crownJewel: false,
			details: [
				{ label: "Hours", values: ["Mon–Fri 08:00–17:00", "Sat 09:00–12:00"] },
				{ label: "Countries", values: ["United States (US)", "Canada (CA)"] }
			]
		})
		const open = { ...BUSINESS, value: { ...BUSINESS.value, week: {}, always_open: true, countries: [] } }
		expect(factView(open as KnowledgeItem, when).details).toEqual([
			{ label: "Hours", values: ["Around the clock"] }
		])
		const zoneOnly = { ...BUSINESS, value: { time_zone: "UTC", week: {}, always_open: false, countries: [] } }
		expect(factView(zoneOnly as KnowledgeItem, when)).toEqual({ headline: "UTC", crownJewel: false, details: [] })
	})

	it("tells the time there, through daylight saving", () => {
		// 2026-11-06 12:00 UTC is a Friday: 05:00 in Denver (MST, UTC-7), 21:00 in Tokyo.
		expect(nowThere("America/Denver", NOW)).toBe("Friday 05:00")
		expect(nowThere("Asia/Tokyo", NOW)).toBe("Friday 21:00")
		// 2026-07-01 12:00 UTC: 06:00 in Denver (MDT, UTC-6).
		expect(nowThere("America/Denver", Date.parse("2026-07-01T12:00:00Z"))).toBe("Wednesday 06:00")
		expect(nowThere("Mars/Olympus_Mons", NOW)).toBeNull()
		expect(nowThere(null, NOW)).toBeNull()
	})
})
