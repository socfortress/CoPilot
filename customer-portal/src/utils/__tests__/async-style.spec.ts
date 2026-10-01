import { readdirSync, readFileSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

/**
 * The portal writes asynchronous code with async/await (#1192). Chains of
 * `.then().catch().finally()` crept in next to it, one style per file; this keeps
 * them from coming back.
 */

const SRC = join(__dirname, "../..")

function sourceFiles(dir: string): string[] {
	return readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
		const path = join(dir, entry.name)
		if (entry.isDirectory()) return entry.name === "__tests__" ? [] : sourceFiles(path)
		return /\.(?:ts|tsx|vue)$/.test(entry.name) ? [path] : []
	})
}

describe("async style", () => {
	it("uses async/await, not .then() chains", () => {
		const offenders = sourceFiles(SRC)
			.filter(file => /\.then\(/.test(readFileSync(file, "utf8")))
			.map(file => relative(SRC, file))
		expect(offenders).toEqual([])
	})
})
