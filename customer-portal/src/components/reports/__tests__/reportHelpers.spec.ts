import { describe, expect, it } from "vitest"
import { elapsedLabel, secondsSince } from "@/utils/elapsed"
import { downloadQueryId, fileNameFromDisposition } from "../reportDownload"

describe("report download helpers", () => {
	it("reads the report id a ?download= names, and nothing else", () => {
		expect(downloadQueryId("42")).toBe(42)
		expect(downloadQueryId(["7", "8"])).toBe(7)
		for (const value of [undefined, null, "", "0", "-3", "4.5", "abc", "12abc", "99999999999999999999"]) {
			expect(downloadQueryId(value)).toBeNull()
		}
	})

	it("takes the file name from Content-Disposition, quoted, bare or encoded", () => {
		expect(fileNameFromDisposition('attachment; filename="weekly report.pdf"')).toBe("weekly report.pdf")
		expect(fileNameFromDisposition("attachment; filename=weekly.pdf")).toBe("weekly.pdf")
		expect(
			fileNameFromDisposition("attachment; filename*=UTF-8''r%C3%A9sum%C3%A9.pdf; filename=\"resume.pdf\"")
		).toBe("résumé.pdf")
		expect(fileNameFromDisposition("attachment; filename*=UTF-8''%E0%A4%A.pdf; filename=\"plain.pdf\"")).toBe(
			"plain.pdf"
		)
		expect(fileNameFromDisposition("attachment")).toBeNull()
		expect(fileNameFromDisposition(undefined)).toBeNull()
	})
})

describe("report timing", () => {
	const now = Date.parse("2026-10-16T10:00:00Z")

	it("reads a stored time as UTC, whatever the viewer's timezone", () => {
		expect(secondsSince("2026-10-16T09:56:30", now)).toBe(210)
		expect(secondsSince("2026-10-16T09:56:30Z", now)).toBe(210)
	})

	it("never reads negative, and gives up on an unreadable time", () => {
		expect(secondsSince("2026-10-16T10:00:20", now)).toBe(0)
		expect(secondsSince("not a date", now)).toBeNull()
	})

	it("says it in a few characters", () => {
		expect([0, 59, 60, 179, 3599, 3600, 3900, 7325].map(elapsedLabel)).toEqual([
			"<1 min",
			"<1 min",
			"1 min",
			"2 min",
			"59 min",
			"1 h 00 min",
			"1 h 05 min",
			"2 h 02 min"
		])
	})
})
