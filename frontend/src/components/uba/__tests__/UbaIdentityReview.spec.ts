import type { UbaIdentityReview, UbaIdentitySummary } from "@/types/uba"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import UbaIdentityReviewPanel from "../UbaIdentityReview.vue"
import { identityDetails, identityLabel } from "../utils"

const getIdentityReview = vi.fn()
const dismissMergeCandidate = vi.fn()
const markIdentityReviewed = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		uba: {
			getIdentityReview: (...a: unknown[]) => getIdentityReview(...a),
			dismissMergeCandidate: (...a: unknown[]) => dismissMergeCandidate(...a),
			markIdentityReviewed: (...a: unknown[]) => markIdentityReviewed(...a),
			searchIdentities: vi.fn(),
			mergeIdentity: vi.fn()
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "yyyy-MM-dd HH:mm" } }) }))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), error: vi.fn() })
}))

function identity(over: Partial<UbaIdentitySummary>): UbaIdentitySummary {
	return {
		id: "x",
		display_name: null,
		kind: "unknown",
		shadow: true,
		privileged: false,
		tags: [],
		aliases: [],
		last_seen: null,
		findings: 0,
		...over
	}
}

const LEARNED = identity({ id: "s1", aliases: ["netbios_sam:CORP\\jdoe"], findings: 2, privileged: true })
const DIRECTORY = identity({ id: "d1", display_name: "John Doe", kind: "human", shadow: false, aliases: ["upn:jdoe@contoso.example"] })

const REVIEW: UbaIdentityReview = {
	has_directory: true,
	candidates: [
		{ id: 7, alias: "upn:jdoe@contoso.example", source: "entra", first_seen: null, last_seen: null, identity: LEARNED, candidate: DIRECTORY }
	],
	unmatched: [identity({ id: "s2", aliases: ["local:win-demo\\svc_backup"], findings: 1 })],
	merges: [
		{
			id: "m1",
			from_identity: "s0",
			into_identity: "d0",
			from_name: "CORP\\asmith",
			into_name: "Ann Smith",
			status: "done",
			requested_by: "admin1",
			requested_at: null,
			done_at: null,
			error: null
		}
	]
}

async function render() {
	const wrapper = mount(UbaIdentityReviewPanel, { props: { customerCode: "lab" } })
	await flushPromises()
	return wrapper
}

describe("ubaIdentityReview", () => {
	beforeEach(() => {
		auth.isAdmin = true
		getIdentityReview.mockReset().mockResolvedValue({ data: REVIEW })
		dismissMergeCandidate.mockReset().mockResolvedValue({ data: {} })
		markIdentityReviewed.mockReset().mockResolvedValue({ data: {} })
	})

	it("names identities by display name, else their strongest alias", () => {
		expect(identityLabel(LEARNED)).toBe("CORP\\jdoe")
		expect(identityLabel(DIRECTORY)).toBe("John Doe")
		expect(identityDetails(LEARNED)).toBe("admin · 2 findings in 14 days · netbios_sam:CORP\\jdoe")
	})

	it("shows candidates, unmatched accounts and recent merges", async () => {
		const text = (await render()).text()
		expect(getIdentityReview).toHaveBeenCalledWith("lab")
		expect(text).toContain("Probably the same person (1)")
		expect(text).toContain("CORP\\jdoe")
		expect(text).toContain("John Doe")
		expect(text).toContain("Accounts not matched to the directory (1)")
		expect(text).toContain("win-demo\\svc_backup")
		expect(text).toContain("CORP\\asmith → Ann Smith")
	})

	it("dismisses a candidate and keeps an account as it is", async () => {
		const wrapper = await render()
		await wrapper.findAll("button").find(b => b.text() === "Not the same")?.trigger("click")
		await wrapper.findAll("button").find(b => b.text() === "Keep as is")?.trigger("click")
		await flushPromises()
		expect(dismissMergeCandidate).toHaveBeenCalledWith("lab", 7)
		expect(markIdentityReviewed).toHaveBeenCalledWith("lab", "s2")
	})

	it("says why there are no suggestions without a directory", async () => {
		getIdentityReview.mockResolvedValue({ data: { ...REVIEW, has_directory: false, candidates: [], unmatched: [] } })
		const text = (await render()).text()
		expect(text).toContain("none is connected for this customer")
		expect(text).not.toContain("Accounts not matched")
	})

	it("analysts see the review but no actions", async () => {
		auth.isAdmin = false
		const wrapper = await render()
		expect(wrapper.text()).toContain("Only admins can merge")
		expect(wrapper.findAll("button").some(b => ["Merge", "Not the same", "Keep as is"].includes(b.text()))).toBe(false)
	})
})
