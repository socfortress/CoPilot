import type { IconifyJSON } from "@iconify/types"
import type { Plugin } from "vite"
import fs from "node:fs"
import path from "node:path"
import { getIcons } from "@iconify/utils"

/**
 * Bundles Iconify icons into the app so nothing is fetched from api.iconify.design at
 * runtime (air-gapped deployments, and no icon names leaking to a third party).
 *
 * Exposes `virtual:iconify-collections`, an array of collections for `addCollection`
 * from `@iconify/vue/offline`:
 *
 * - `serve`: the whole collections, so a newly used icon works without a restart.
 * - `build`: only the icons whose full name (`carbon:chevron-down`) appears in `srcDir`.
 *   A name that is not in its collection fails the build, which catches typos that
 *   would otherwise render as an empty box. Names must therefore be written out in
 *   full: a name assembled at runtime (`"carbon:" + x`) is not found by the scan.
 */

const VIRTUAL_ID = "virtual:iconify-collections"
const RESOLVED_ID = `\0${VIRTUAL_ID}`
const SOURCE_EXTENSIONS = new Set([".vue", ".ts", ".tsx"])

function listSourceFiles(dir: string): string[] {
	return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
		const fullPath = path.join(dir, entry.name)
		if (entry.isDirectory()) return listSourceFiles(fullPath)
		return SOURCE_EXTENSIONS.has(path.extname(entry.name)) ? [fullPath] : []
	})
}

function usedIconNames(srcDir: string, prefixes: string[]): Map<string, Set<string>> {
	const pattern = new RegExp(`\\b(${prefixes.join("|")}):([a-z0-9]+(?:-[a-z0-9]+)*)\\b`, "g")
	const used = new Map(prefixes.map(prefix => [prefix, new Set<string>()]))

	for (const file of listSourceFiles(srcDir)) {
		for (const [, prefix, name] of fs.readFileSync(file, "utf8").matchAll(pattern)) {
			used.get(prefix!)!.add(name!)
		}
	}
	return used
}

function hasIcon(collection: IconifyJSON, name: string): boolean {
	return name in collection.icons || name in (collection.aliases ?? {})
}

export function iconifyCollections(options: { collections: IconifyJSON[]; srcDir: string }): Plugin {
	let command: "serve" | "build" = "serve"

	return {
		name: "iconify-collections",
		configResolved(config) {
			command = config.command
		},
		resolveId(id) {
			return id === VIRTUAL_ID ? RESOLVED_ID : undefined
		},
		load(id) {
			if (id !== RESOLVED_ID) return

			if (command === "serve") {
				return `export default ${JSON.stringify(options.collections)}`
			}

			const used = usedIconNames(
				options.srcDir,
				options.collections.map(collection => collection.prefix)
			)
			const missing: string[] = []
			const subsets: IconifyJSON[] = []

			for (const collection of options.collections) {
				const names = [...used.get(collection.prefix)!]
				missing.push(...names.filter(name => !hasIcon(collection, name)).map(name => `${collection.prefix}:${name}`))

				const subset = names.length ? getIcons(collection, names) : null
				if (subset) subsets.push(subset)
			}

			if (missing.length) {
				this.error(`Unknown icons (not in their Iconify collection): ${missing.sort().join(", ")}`)
			}

			return `export default ${JSON.stringify(subsets)}`
		}
	}
}
