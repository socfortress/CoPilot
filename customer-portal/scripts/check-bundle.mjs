#!/usr/bin/env node
/**
 * Bundle budget for the Customer Portal (#1185). Builds into a temp dir and fails when:
 *
 * - a shiki grammar outside utils/highlighter.ts is emitted — what importing from
 *   "shiki" instead of "shiki/core" does (it registers all ~200 languages);
 * - WebAssembly is emitted (the Oniguruma engine: the portal uses the JavaScript one);
 * - a page is pulled into the entry chunk instead of loading with its route. Only the
 *   login page (views/Auth.vue) is imported statically, on purpose;
 * - the entry chunk grows past ENTRY_GZIP_BUDGET_KB.
 *
 *   pnpm check:bundle
 */
import { execFileSync } from "node:child_process"
import { mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { basename, join } from "node:path"
import process from "node:process"
import { fileURLToPath, URL } from "node:url"
import { gzipSync } from "node:zlib"

const ENTRY_GZIP_BUDGET_KB = 320 // 302 KB after #1185; room for growth, not for a regression
const STATIC_VIEWS = new Set(["src/views/Auth.vue"])

const root = fileURLToPath(new URL("..", import.meta.url))
const outDir = mkdtempSync(join(tmpdir(), "portal-bundle-"))
const failures = []

try {
	execFileSync(
		join(root, "node_modules/.bin/vite"),
		["build", "--manifest", "--outDir", outDir, "--logLevel", "error"],
		{
			cwd: root,
			stdio: ["ignore", "ignore", "inherit"]
		}
	)

	const assets = readdirSync(join(outDir, "assets"))
	const chunkName = file => basename(file).replace(/-[\w-]{8}\.js$/, "")

	// 1. Only the declared grammars.
	const declared = new Set(
		[...readFileSync(join(root, "src/utils/highlighter.ts"), "utf8").matchAll(/shiki\/langs\/([\w-]+)\.mjs/g)].map(
			m => m[1]
		)
	)
	const allGrammars = new Set(
		readdirSync(join(root, "node_modules/shiki/dist/langs"))
			.filter(file => file.endsWith(".mjs"))
			.map(file => file.replace(/\.mjs$/, ""))
	)
	const emittedGrammars = [
		...new Set(
			assets
				.filter(file => file.endsWith(".js"))
				.map(chunkName)
				.filter(name => allGrammars.has(name))
		)
	]
	const undeclared = emittedGrammars.filter(name => !declared.has(name))
	if (undeclared.length)
		failures.push(`shiki grammars not declared in utils/highlighter.ts: ${undeclared.join(", ")}`)

	// 2. No WebAssembly.
	const wasm = assets.filter(file => file.endsWith(".wasm") || chunkName(file) === "wasm")
	if (wasm.length) failures.push(`WebAssembly in the bundle: ${wasm.join(", ")}`)

	// 3. Pages load with their route, not with the entry chunk. A page imported
	// statically is merged into a shared chunk and vanishes from the manifest as its own
	// entry, so each page the router names must be there as a dynamic entry.
	const manifest = JSON.parse(readFileSync(join(outDir, ".vite/manifest.json"), "utf8"))
	const entryKey = Object.keys(manifest).find(key => manifest[key].isEntry)
	const routedViews = [
		...new Set(
			[
				...readFileSync(join(root, "src/router/index.ts"), "utf8").matchAll(
					/["']@\/views\/([\w/.-]+\.vue)["']/g
				)
			].map(m => `src/views/${m[1]}`)
		)
	].filter(view => !STATIC_VIEWS.has(view))
	const eager = routedViews.filter(view => !manifest[view]?.isDynamicEntry)
	if (eager.length)
		failures.push(`pages bundled with the app instead of loading with their route: ${eager.join(", ")}`)

	// 4. Entry size.
	const entryFile = manifest[entryKey].file
	const entryGzipKb = gzipSync(readFileSync(join(outDir, entryFile))).length / 1024
	if (entryGzipKb > ENTRY_GZIP_BUDGET_KB)
		failures.push(`entry chunk ${entryGzipKb.toFixed(0)} KB gzip > budget ${ENTRY_GZIP_BUDGET_KB} KB`)

	console.log(
		`grammars: ${emittedGrammars.length} (declared ${declared.size}) · wasm: ${wasm.length} · lazy pages: ${routedViews.length - eager.length}/${routedViews.length} · entry: ${entryGzipKb.toFixed(0)} KB gzip (budget ${ENTRY_GZIP_BUDGET_KB})`
	)
} finally {
	rmSync(outDir, { recursive: true, force: true })
}

if (failures.length) {
	console.error(`\nBundle check failed:\n${failures.map(failure => `  - ${failure}`).join("\n")}`)
	process.exit(1)
}
console.log("Bundle check passed.")
