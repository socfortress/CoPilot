/** Pure matching/parsing logic for SearchDialog, split out so it can be unit-tested. */
import type { IFuseOptions } from "fuse.js"
import Fuse from "fuse.js"

/** The two entity kinds `entityCandidates` can emit; a subset of SearchDialog's `ItemKind`. */
export type EntityCandidateKind = "alert" | "case"

export interface EntityCandidate {
	kind: EntityCandidateKind
	target: string
	title: string
}

const FUSE_OPTIONS = { threshold: 0.4, ignoreLocation: true }

/** Builds a reusable Fuse index over a stable list — construct once, `searchFuse` many times. */
export function createFuse<T>(items: T[], keys: IFuseOptions<T>["keys"]): Fuse<T> {
	return new Fuse(items, { keys, ...FUSE_OPTIONS })
}

/** Runs a query against a pre-built Fuse index; an empty query returns `all` unchanged. */
export function searchFuse<T>(fuse: Fuse<T>, query: string, all: T[]): T[] {
	if (!query.trim()) return all
	return fuse.search(query).map(result => result.item)
}

/**
 * Ranked fuzzy filter over a list, backed by Fuse.js. Convenience wrapper that builds a
 * fresh index each call — use `createFuse` + `searchFuse` on hot paths over stable lists.
 */
export function fuzzyFilter<T>(items: T[], query: string, keys: IFuseOptions<T>["keys"]): T[] {
	return searchFuse(createFuse(items, keys), query, items)
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
		{ kind: "alert" as const, target: numeric, title: `Go to Alert #${numeric}` },
		{ kind: "case" as const, target: numeric, title: `Go to Case #${numeric}` }
	]
}
