import { describe, expect, it } from "vitest"
import { PASSWORD_PROBLEMS, PASSWORD_REQUIREMENTS, passwordProblem, passwordProblemCode } from "../password-policy"
import fixture from "./fixtures/password-policy-cases.json"

// The cases backend/tests/test_password_policy.py runs against the API's policy (#1265).
describe("password policy, the same as the API's", () => {
	it("words every rule as the API does", () => {
		expect(PASSWORD_PROBLEMS).toEqual(fixture.messages)
		expect(PASSWORD_REQUIREMENTS).toBe(fixture.requirements)
	})

	it.each(fixture.cases.map(c => [c.problem ?? "ok", c.note || JSON.stringify(c.password), c] as const))(
		"%s: %s",
		(_problem, _note, c) => {
			expect(passwordProblemCode(c.password)).toBe(c.problem)
		}
	)

	it("accepts the password from #1265", () => {
		expect(passwordProblem("Password1!-x")).toBeNull()
	})

	it("refuses a lone surrogate, which the shared cases cannot carry", () => {
		expect(passwordProblemCode("Aa1!aaaa\uD800")).toBe("control_character")
	})

	it("names the rule a password breaks", () => {
		expect(passwordProblem("password1!")).toBe("Password must contain an uppercase letter")
	})
})
