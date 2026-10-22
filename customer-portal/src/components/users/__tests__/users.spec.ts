import { describe, expect, it } from "vitest"
import { inviteProblems, sortUsers, statusTags } from "../users"
import { tenantUser } from "./fixtures"

/** The Users page's rules (#1296): the API's own, so the form never sends what it refuses. */
describe("an invitation", () => {
	it("needs the API's username, an email and a customer", () => {
		expect(inviteProblems({ username: "jane.doe", email: "jane@acme.example", customerCodes: ["ACME"] })).toEqual(
			{}
		)
		const problems = inviteProblems({ username: "", email: "", customerCodes: [] })
		expect(Object.keys(problems).sort()).toEqual(["customerCodes", "email", "username"])
	})

	it("refuses what the API's username rule refuses", () => {
		for (const bad of ["ab", "-jane", "jane doe", "jane<x>", "x".repeat(65)]) {
			expect(inviteProblems({ username: bad, email: "j@a.io", customerCodes: ["A"] }).username).toContain(
				"3 to 64"
			)
		}
		for (const good of ["jan", "Jane_Doe", "jane@acme", "j.d-1", "x".repeat(64)]) {
			expect(inviteProblems({ username: good, email: "j@a.io", customerCodes: ["A"] }).username).toBeUndefined()
		}
	})

	it("refuses an email without a domain", () => {
		expect(inviteProblems({ username: "jane", email: "jane@acme", customerCodes: ["A"] }).email).toBeDefined()
		expect(
			inviteProblems({ username: "jane", email: "jane@sub.acme.io", customerCodes: ["A"] }).email
		).toBeUndefined()
	})
})

describe("a user's state", () => {
	it("says who it is, whether they administer, and whether they can sign in", () => {
		expect(statusTags(tenantUser(1, "me", { is_self: true, is_customer_admin: true })).map(t => t.key)).toEqual([
			"self",
			"admin"
		])
		expect(
			statusTags(tenantUser(2, "gone", { disabled: true, must_change_password: true })).map(t => t.key)
		).toEqual(["disabled"])
		expect(statusTags(tenantUser(3, "new", { must_change_password: true })).map(t => t.key)).toEqual(["password"])
		expect(statusTags(tenantUser(4, "plain"))).toEqual([])
	})

	it("lists the caller first and those who can't sign in last", () => {
		const users = [
			tenantUser(1, "gone", { disabled: true }),
			tenantUser(2, "b"),
			tenantUser(3, "me", { is_self: true })
		]
		expect(sortUsers(users).map(u => u.username)).toEqual(["me", "b", "gone"])
	})
})
