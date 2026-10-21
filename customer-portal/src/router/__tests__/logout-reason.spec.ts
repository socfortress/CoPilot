import type { RouteLocation } from "vue-router"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/api", () => ({ default: {} }))

const { default: router } = await import("../index")

function redirectOf(query: Record<string, string>) {
	const record = router.getRoutes().find(route => route.name === "Logout")
	const redirect = record?.redirect as (to: RouteLocation) => unknown
	return redirect({ query } as unknown as RouteLocation)
}

/** Signing out carries a known reason to the sign-in page, and nothing else (#1296). */
describe("the sign-out route", () => {
	it("keeps the disabled-account reason", () => {
		expect(redirectOf({ reason: "disabled" })).toEqual({ path: "/login", query: { reason: "disabled" } })
	})

	it("drops anything else", () => {
		expect(redirectOf({})).toEqual({ path: "/login", query: {} })
		expect(redirectOf({ reason: "<script>", x: "1" })).toEqual({ path: "/login", query: {} })
	})
})
