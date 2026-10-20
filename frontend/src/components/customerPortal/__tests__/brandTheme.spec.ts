import { colord, extend } from "colord"
import a11yPlugin from "colord/plugins/a11y"
import { describe, expect, it } from "vitest"
import { loginPrimary } from "../brandTheme"

extend([a11yPlugin])

describe("loginPrimary", () => {
	it("is the default theme while the switch is off, without a color or with a bad one", () => {
		expect(loginPrimary("#215ac8", false)).toBeNull()
		expect(loginPrimary("#215ac8", null)).toBeNull()
		expect(loginPrimary(null, true)).toBeNull()
		expect(loginPrimary("blue", true)).toBeNull()
	})

	it("keeps a color that stands out on white, with white text", () => {
		expect(loginPrimary("#215ac8", true)).toEqual({ primary: "#215ac8", onPrimary: "#ffffff" })
	})

	it("darkens a pale color until it stands out on white", () => {
		const palette = loginPrimary("#ffe066", true)
		if (!palette) throw new Error("expected a palette")
		expect(colord(palette.primary).contrast("#ffffff")).toBeGreaterThanOrEqual(3)
		expect(colord(palette.onPrimary).contrast(palette.primary)).toBeGreaterThanOrEqual(4.5)
	})
})
