/** Pure event-source resolution for Event Search, split out so it can be unit-tested. */
import type { EventSource } from "@/types/event-sources"

/** Regex metacharacters that must survive as literals. `*` and `?` are absent on purpose — they are the glob. */
const REGEX_METACHARACTERS_RE = /[.+^${}()|[\]\\]/g
const STAR_RE = /\*/g
const QUESTION_MARK_RE = /\?/g
const GLOB_RE = /[*?]/g

/**
 * `fnmatch`-style match of one concrete index against an event source's pattern.
 *
 * Deliberately the same semantics the backend applies in
 * `app/siem/services/events.py:_index_matches_pattern`, so a source resolved here is one
 * the server would also accept: `*` matches any run, `?` matches one character, and
 * everything else is literal. The escaping is the load-bearing part — index names are
 * made of dots, and an unescaped `.` would let `wazuh-alerts-*` claim `wazuh_alerts_x`.
 *
 * As on the backend, Elasticsearch's comma-separated lists and `-foo-*` exclusions are
 * not supported; an event source's pattern is a single glob.
 */
export function indexMatchesPattern(indexName: string, indexPattern: string): boolean {
	if (!indexName || !indexPattern) return false

	const expression = indexPattern
		.replace(REGEX_METACHARACTERS_RE, "\\$&")
		.replace(STAR_RE, ".*")
		.replace(QUESTION_MARK_RE, ".")

	return new RegExp(`^${expression}$`).test(indexName)
}

/** How much of a pattern is literal — the measure of how specific it is. */
function literalLength(indexPattern: string): number {
	return indexPattern.replace(GLOB_RE, "").length
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
 * catch-all `*`, which a deployment can legitimately have alongside it.
 */
export function resolveSourceForIndex(indexName: string, eventSources: EventSource[]): EventSource | null {
	const matches = eventSources.filter(
		source => source.enabled && indexMatchesPattern(indexName, source.index_pattern)
	)

	if (!matches.length) return null

	return matches.reduce((best, candidate) =>
		literalLength(candidate.index_pattern) > literalLength(best.index_pattern) ? candidate : best
	)
}
