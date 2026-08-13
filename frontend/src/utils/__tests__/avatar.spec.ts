import { describe, expect, it } from "vitest"
import { getAvatar } from "../index"

function decode(uri: string) {
	return decodeURIComponent(uri.replace("data:image/svg+xml;utf8,", ""))
}

describe("getAvatar (oreo silk)", () => {
	it("returns a data uri, not a vercel url", () => {
		const uri = getAvatar({ seed: "JD", text: "JD", size: 64 })
		expect(uri.startsWith("data:image/svg+xml")).toBe(true)
		expect(uri).not.toContain("vercel")
	})

	it("is deterministic for the same seed", () => {
		expect(getAvatar({ seed: "JD", text: "JD" })).toBe(getAvatar({ seed: "JD", text: "JD" }))
	})

	it("varies palette across seeds", () => {
		const seeds = ["JD", "AB", "ZZ", "socfortress", "MR", "QQ"]
		const uniq = new Set(seeds.map(s => getAvatar({ seed: s, text: s })))
		expect(uniq.size).toBe(seeds.length)
	})

	it("renders white initials on top of the gradient", () => {
		const svg = decode(getAvatar({ seed: "JD", text: "JD", size: 64 }))
		expect(svg).toContain('fill="#ffffff"')
		expect(svg).toContain(">JD</text>")
		// overlay must be the last child so it paints above the gradient
		expect(svg.indexOf("<text")).toBeGreaterThan(svg.lastIndexOf("<path"))
	})

	it("escapes xml-unsafe initials", () => {
		const svg = decode(getAvatar({ seed: "x", text: "<&>", size: 32 }))
		expect(svg).toContain("&lt;&amp;&gt;")
		expect(svg).not.toContain("><&></text>")
	})

	it("omits the text node when no initials given", () => {
		const svg = decode(getAvatar({ seed: "JD" }))
		expect(svg).not.toContain("<text")
	})

	it("honours size and defaults to 32", () => {
		expect(decode(getAvatar({ seed: "a", text: "a", size: 64 }))).toContain('width="64"')
		expect(decode(getAvatar({ seed: "a", text: "a" }))).toContain('width="32"')
	})

	it("does not throw on empty seed", () => {
		expect(() => getAvatar({ seed: "", text: "" })).not.toThrow()
	})
})
