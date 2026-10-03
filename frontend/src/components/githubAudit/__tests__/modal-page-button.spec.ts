import type { VueWrapper } from "@vue/test-utils"
import type { Router } from "vue-router"
import { flushPromises } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import FeedbackDashboardRecentReviews from "@/components/aiAnalyst/Feedback/FeedbackDashboardRecentReviews.vue"
import { mountWithRouter } from "@/components/common/__tests__/modal-page-harness"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import GitHubAuditCard from "../GitHubAuditCard.vue"

/**
 * Entity drawers whose entity also has a page — a GitHub audit configuration, an AI
 * analyst review — offer that page from their header; following it closes the drawer.
 */

vi.mock("@/api", async () => {
	const { pendingApi } = await import("@/components/common/__tests__/modal-page-stubs")
	return { default: pendingApi() }
})
vi.mock("naive-ui", async importOriginal => {
	const { stubOverlays } = await import("@/components/common/__tests__/modal-page-stubs")
	return stubOverlays(await importOriginal<Record<string, unknown>>())
})

async function expectPageLink(wrapper: VueWrapper, router: Router, href: string, label: string) {
	// The drawer, not its content: the outermost overlay that carries the button.
	const holder = wrapper
		.findAll("[data-testid=overlay-stub]")
		.find(candidate => candidate.find("[data-testid=modal-page-button]").exists())
	if (!holder) throw new Error("no overlay carries a page button")
	const overlay = () => holder.attributes("data-show")
	expect(overlay()).toBe("true")
	const link = holder.get("[data-testid=modal-page-button]")
	expect(link.attributes("href")).toBe(href)
	expect(link.attributes("aria-label")).toBe(label)
	await link.trigger("click", { button: 0 })
	await flushPromises()
	expect(overlay()).toBe("false")
	expect(router.currentRoute.value.fullPath).toBe(href)
}

describe("entity drawers with a page of their own", () => {
	it("gitHub audit configuration → its page", async () => {
		const config = { id: 4, organization: "socfortress", enabled: true, auto_audit_enabled: false }
		const { wrapper, router } = await mountWithRouter(GitHubAuditCard, { config }, [
			"GitHubAuditDetail",
			"GitHubAuditConfigForm"
		])
		wrapper.findComponent(EntityDetailsButton).vm.$emit("view")
		await flushPromises()
		await expectPageLink(wrapper, router, "/github-audit/4", "Open the audit's page")
	})

	it("aI analyst review → its feedback page", async () => {
		const review = {
			id: 12,
			report_id: 88,
			overall_verdict: "correct",
			ioc_reviews: [],
			created_at: "2026-09-01T00:00:00",
			updated_at: "2026-09-01T00:00:00"
		}
		const { wrapper, router } = await mountWithRouter(
			FeedbackDashboardRecentReviews,
			{ stats: { recent_reviews: [review] } },
			["FeedbackDashboardRecentReviewDetail"]
		)
		expect(wrapper.find("[data-testid=modal-page-button]").exists()).toBe(false) // nothing open yet
		wrapper.findComponent(EntityDetailsButton).vm.$emit("view")
		await flushPromises()
		await expectPageLink(wrapper, router, "/ai-analyst/feedback/12", "Open the review's page")
	})
})
