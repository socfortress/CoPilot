import { describe, expect, it } from "vitest"
import { AuthUserRole } from "@/types/auth"
import {
	needsCustomers,
	ROLE_NAME_OPTIONS,
	roleColor,
	roleDescription,
	roleLabel,
	roleNameOf,
	roleTagType,
	seesEveryCustomer
} from "../roles"

describe("user roles and customers (#1219)", () => {
	it("offers the responder role", () => {
		expect(ROLE_NAME_OPTIONS.map(option => option.value)).toContain("responder")
	})

	it("requires customers for analysts and responders, by name or id", () => {
		for (const role of ["analyst", "Responder", AuthUserRole.Analyst, AuthUserRole.Responder]) {
			expect(needsCustomers(role), String(role)).toBe(true)
		}
		for (const role of ["admin", "customer_user", "scheduler", AuthUserRole.Admin, null, undefined]) {
			expect(needsCustomers(role), String(role)).toBe(false)
		}
	})

	it("knows admins see every customer", () => {
		expect(seesEveryCustomer("admin")).toBe(true)
		expect(seesEveryCustomer(AuthUserRole.Admin)).toBe(true)
		expect(seesEveryCustomer("responder")).toBe(false)
	})

	it("gives the three SOC roles three colours, no two of them yellow", () => {
		expect(roleTagType("admin")).toBe("error")
		expect(roleTagType("analyst")).toBe("info")
		expect(roleTagType("responder")).toBe("primary")
		expect(new Set(["admin", "analyst", "responder"].map(roleTagType)).size).toBe(3)
		expect(roleColor("analyst")).toBe("var(--info-color)")
		expect(roleColor("scheduler")).toBe("var(--fg-tertiary-color)")
	})

	it("says in one line what each role may do", () => {
		for (const { value } of ROLE_NAME_OPTIONS) expect(roleDescription(value), value).not.toBe("")
		expect(roleDescription("responder")).toMatch(/act on the endpoints/)
	})

	it("names a role from its id, as the API spells it", () => {
		expect(roleNameOf(AuthUserRole.Responder)).toBe("responder")
		expect(roleNameOf(AuthUserRole.CustomerUser)).toBe("customer_user")
		expect(roleNameOf(AuthUserRole.Unknown)).toBe("")
		expect(roleNameOf(undefined)).toBe("")
	})

	it("labels a role the way the role pickers do", () => {
		expect(roleLabel("customer_user")).toBe("Customer User")
		expect(roleLabel("RESPONDER")).toBe("Responder")
		expect(roleLabel("something_else")).toBe("something_else")
	})
})
