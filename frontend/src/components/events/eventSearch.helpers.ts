/** Pure helpers for Event Search, split out so they can be unit-tested. */
import type { EventSource } from "@/types/event-sources"
import type { FieldMapping } from "@/types/events"

/** How many sources one search may cover. The backend refuses more (`app/siem/schema/events.py:MAX_SOURCES`). */
export const MAX_SOURCES = 5

/** Regex metacharacters that must survive as literals. `*` and `?` are absent on purpose — they are the glob. */
const REGEX_METACHARACTERS_RE = /[.+^${}()|[\]\\]/g
const STAR_RE = /\*/g
const QUESTION_MARK_RE = /\?/g
const GLOB_RE = /[*?]/g

/** Text in double quotes, escaped quotes included: a query's values, never its field names. */
const QUOTED_RE = /"(?:[^"\\]|\\.)*"/g
/** `field:` at the start of a term: after whitespace, `(` or an operator (`+`, `-`, `!`). */
const FIELD_REFERENCE_RE = /(?:^|[\s(+!-])([A-Z_@][\w.@-]*)\s*:/gi

/** One glob against one index: `*` matches any run, `?` one character, everything else is literal. */
function globMatches(indexName: string, glob: string): boolean {
	const expression = glob.replace(REGEX_METACHARACTERS_RE, "\\$&").replace(STAR_RE, ".*").replace(QUESTION_MARK_RE, ".")

	return new RegExp(`^${expression}$`).test(indexName)
}

function patternParts(indexPattern: string): string[] {
	return indexPattern
		.split(",")
		.map(part => part.trim())
		.filter(Boolean)
}

/**
 * Whether the indexer would search `indexName` for an event source's pattern.
 *
 * The same rule the backend applies in `app/siem/services/events.py:index_in_pattern`, so a
 * source resolved here is one the server would also accept. A pattern is a comma list of
 * globs, read left to right as the indexer reads it: a part starting with `-` removes what
 * the parts before it matched, and a later part can add an index back. Within a glob, the
 * escaping is the load-bearing part — index names are made of dots, and an unescaped `.`
 * would let `wazuh-alerts-*` claim `wazuh_alerts_x`.
 */
export function indexMatchesPattern(indexName: string, indexPattern: string): boolean {
	if (!indexName || !indexPattern) return false

	let included = false
	for (const part of patternParts(indexPattern)) {
		if (part.startsWith("-")) {
			if (included && globMatches(indexName, part.slice(1))) included = false
		} else if (globMatches(indexName, part)) {
			included = true
		}
	}

	return included
}

/** How literally a pattern names an index: the literal length of its longest part matching it. */
function specificity(indexName: string, indexPattern: string): number {
	return Math.max(
		-1,
		...patternParts(indexPattern)
			.filter(part => !part.startsWith("-") && globMatches(indexName, part))
			.map(part => part.replace(GLOB_RE, "").length)
	)
}

/**
 * The event source a concrete index belongs to, or `null` when none claims it.
 *
 * An alert knows the index it was read from but not the source that produced it: the two
 * are joined only by the pattern, since an event source's name is whatever the operator
 * typed. This is that join.
 *
 * Disabled sources are skipped — they are not selectable in the filter bar, so resolving
 * to one would leave the select showing something the user cannot choose. When several
 * patterns match the same index, the most specific wins: `office365-acme-*` beats a
 * catch-all `*`, which a deployment can legitimately have alongside it. On a tie, the
 * first in the list, as on the backend (`source_for_index`).
 */
export function resolveSourceForIndex(indexName: string, eventSources: EventSource[]): EventSource | null {
	const matches = eventSources.filter(
		source => source.enabled && indexMatchesPattern(indexName, source.index_pattern)
	)

	if (!matches.length) return null

	return matches.reduce((best, candidate) =>
		specificity(indexName, candidate.index_pattern) > specificity(indexName, best.index_pattern) ? candidate : best
	)
}

/**
 * When sources can't be searched together because they name different time fields, each
 * source with its field (`Firewall: timestamp, Cloud: @timestamp`); otherwise `null`.
 *
 * One search sorts every source's events on one field, so the backend refuses sources that
 * name different ones. Checked here too, so the filter bar can say so before anything is sent.
 */
export function timeFieldMismatch(sources: Pick<EventSource, "name" | "time_field">[]): string | null {
	if (new Set(sources.map(source => source.time_field)).size <= 1) return null

	return sources.map(source => `${source.name}: ${source.time_field}`).join(", ")
}

/** The fields a Lucene query names (`field:value`), each once, in the order they appear. Quoted text is skipped. */
export function fieldsInQuery(query: string): string[] {
	const unquoted = query.replace(QUOTED_RE, match => " ".repeat(match.length))
	const fields = new Set<string>()
	for (const match of unquoted.matchAll(FIELD_REFERENCE_RE)) {
		fields.add(match[1])
	}

	return [...fields]
}

/**
 * The fields `query` names that the searched sources' indices type differently (`conflict`).
 *
 * A query on such a field can silently miss events: the indexer reads the query against each
 * index's own type, and an index where the value can't be read that way matches nothing,
 * without an error (a CIDR on a field that is an `ip` in one source and a `keyword` in another
 * finds only the first source's events).
 */
export function conflictingFieldsInQuery(query: string, fieldMappings: FieldMapping[]): FieldMapping[] {
	const conflicts = new Map(fieldMappings.filter(mapping => mapping.conflict).map(mapping => [mapping.field, mapping]))

	return fieldsInQuery(query)
		.map(field => conflicts.get(field))
		.filter((mapping): mapping is FieldMapping => mapping !== undefined)
}

/** The source names a route query carries (`?source_name=A&source_name=B`), each once, blanks dropped. */
export function routeSourceNames(raw: unknown): string[] {
	const values = Array.isArray(raw) ? raw : [raw]
	const names = values.filter((value): value is string => typeof value === "string").map(value => value.trim())

	return [...new Set(names.filter(Boolean))]
}
