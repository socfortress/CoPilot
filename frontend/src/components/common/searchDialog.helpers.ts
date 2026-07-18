/** Pure matching/parsing logic for SearchDialog, split out so it can be unit-tested. */
import type { IFuseOptions } from "fuse.js"
import Fuse from "fuse.js"

/** What an entity jump points at. Mirrors `ItemKind` in SearchDialog.vue. */
export type EntityKind = "alert" | "case" | "customer" | "agent"

export interface EntityCandidate {
	kind: EntityKind
	target: string
	title: string
}

/**
 * Ranked fuzzy filter over a list, backed by Fuse.js. An empty query returns the
 * list unchanged; otherwise results come back in Fuse's relevance order.
 * `ignoreLocation` so a match late in the string still counts.
 */
export function fuzzyFilter<T>(items: T[], query: string, keys: IFuseOptions<T>["keys"]): T[] {
	if (!query.trim()) return items

	const fuse = new Fuse(items, { keys, threshold: 0.4, ignoreLocation: true })
	return fuse.search(query).map(result => result.item)
}

/** Splits a raw query into keywords (whitespace-separated, empties dropped) for highlighting. */
export function toKeywords(search: string): string[] {
	return search.trim().split(/\s+/).filter(Boolean)
}

/**
 * Builds the "jump to entity by ID/code" quick candidates for a query:
 * - a numeric query (optionally `#`-prefixed) → Alert and Case by ID
 * A multi-word query yields none (it's a text search, not an identifier).
 */
export function entityCandidates(search: string): EntityCandidate[] {
	const query = search.trim()
	if (!query) return []

	const numeric = query.replace(/^#/, "")
	if (!/^\d+$/.test(numeric)) return []

	return [
		{ kind: "alert", target: numeric, title: `Go to Alert #${numeric}` },
		{ kind: "case", target: numeric, title: `Go to Case #${numeric}` }
	]
}
