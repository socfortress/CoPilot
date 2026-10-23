import type {
	CustomerHealthcheckSource,
	UnhealthyAgentDeleteResult,
	UnhealthyAgentPreview,
	UnhealthyAgentsDeletion,
	UnhealthyAgentsPreview,
	UnhealthyAgentVerdict,
	UnhealthyDeleteThreshold
} from "@/types/customers"

/**
 * Deleting a customer's unhealthy agents from the healthcheck lists (#1291). Pure: the dialog renders
 * what these decide, and the backend judges every agent again, so nothing here is trusted by it.
 */

// The backend's bounds (healthchecks/agents/schema/unhealthy_delete.py): checked here so the dialog
// says why before asking, never instead of the server.
export const MIN_THRESHOLD_HOURS = 24
export const MAX_THRESHOLD_DAYS = 3650
/** Under a week, machines merely switched off (a weekend, a holiday) may be included. */
export const CAUTION_BELOW_DAYS = 7
/**
 * Each agent costs a call to Wazuh and to Velociraptor: small chunks keep each request short and
 * the progress honest. The backend refuses more than 50.
 */
export const DELETE_CHUNK_SIZE = 10
/** A preview only reads the database; the backend accepts up to 1000 ids. */
export const PREVIEW_CHUNK_SIZE = 1000

export const DEFAULT_THRESHOLD: UnhealthyDeleteThreshold = { value: 30, unit: "days" }

export const THRESHOLD_PRESETS: { key: string; label: string; threshold: UnhealthyDeleteThreshold }[] = [
	{ key: "24h", label: "24 h", threshold: { value: 24, unit: "hours" } },
	{ key: "7d", label: "7 d", threshold: { value: 7, unit: "days" } },
	{ key: "30d", label: "30 d", threshold: { value: 30, unit: "days" } },
	{ key: "90d", label: "90 d", threshold: { value: 90, unit: "days" } }
]

export type ListFilter = Partial<{ time: number; unit: "minutes" | "hours" | "days" }>

export function thresholdHours(threshold: UnhealthyDeleteThreshold): number {
	return threshold.unit === "days" ? threshold.value * 24 : threshold.value
}

/** Why the threshold cannot be sent, or null when it can. */
export function thresholdProblem(threshold: Partial<UnhealthyDeleteThreshold>): string | null {
	const { value, unit } = threshold
	if (value === undefined || value === null || Number.isNaN(value) || !unit) {
		return "Choose how long the agents must have gone unseen."
	}
	if (!Number.isInteger(value) || value < 1) return "Use a whole number of hours or days."
	const hours = thresholdHours({ value, unit })
	if (hours < MIN_THRESHOLD_HOURS) return "At least 24 hours: an agent unseen for less is offline, not gone."
	if (hours > MAX_THRESHOLD_DAYS * 24) return `At most ${MAX_THRESHOLD_DAYS} days.`
	return null
}

/**
 * The dialog's starting threshold: the list's own filter when it is a valid one, so the dialog
 * deletes by the rule the list was read with; otherwise 30 days. Minutes are rounded up to hours,
 * never down: a longer threshold deletes less.
 */
export function thresholdFromListFilter(filter: ListFilter): UnhealthyDeleteThreshold {
	const { time, unit } = filter
	if (!time || !unit) return { ...DEFAULT_THRESHOLD }
	const threshold: UnhealthyDeleteThreshold =
		unit === "days"
			? { value: time, unit: "days" }
			: { value: unit === "hours" ? time : Math.ceil(time / 60), unit: "hours" }
	return thresholdProblem(threshold) ? { ...DEFAULT_THRESHOLD } : threshold
}

/** The preset the threshold equals, by duration (24 hours and 1 day are the same preset). */
export function presetKey(threshold: Partial<UnhealthyDeleteThreshold>): string | null {
	if (thresholdProblem(threshold)) return null
	const hours = thresholdHours(threshold as UnhealthyDeleteThreshold)
	return THRESHOLD_PRESETS.find(preset => thresholdHours(preset.threshold) === hours)?.key ?? null
}

export function thresholdLabel(threshold: UnhealthyDeleteThreshold): string {
	const unit = threshold.value === 1 ? threshold.unit.slice(0, -1) : threshold.unit
	return `${threshold.value} ${unit}`
}

export function sameThreshold(a: UnhealthyDeleteThreshold | null, b: UnhealthyDeleteThreshold | null): boolean {
	return !!a && !!b && a.value === b.value && a.unit === b.unit
}

export function needsCaution(threshold: UnhealthyDeleteThreshold): boolean {
	return thresholdHours(threshold) < CAUTION_BELOW_DAYS * 24
}

/**
 * Whether what was typed confirms deleting ``count`` agents. Every deletion asks for it, however few
 * the agents and however long the threshold: it cannot be undone.
 */
export function confirmationMatches(typed: string, count: number): boolean {
	return typed.trim() === String(count)
}

export function chunk<T>(items: T[], size: number): T[][] {
	const chunks: T[][] = []
	for (let index = 0; index < items.length; index += size) chunks.push(items.slice(index, index + size))
	return chunks
}

export function toolName(source: CustomerHealthcheckSource): string {
	return source === "wazuh" ? "Wazuh" : "Velociraptor"
}

export function otherTool(source: CustomerHealthcheckSource): CustomerHealthcheckSource {
	return source === "wazuh" ? "velociraptor" : "wazuh"
}

/** One preview from the answers to its chunks, in request order. */
export function mergePreviews(parts: UnhealthyAgentsPreview[]): UnhealthyAgentsPreview {
	const [first] = parts
	const counts = { deletable: 0, active_elsewhere: 0, seen_recently: 0, wazuh_manager: 0, not_found: 0 }
	for (const part of parts) {
		for (const verdict of Object.keys(counts) as UnhealthyAgentVerdict[])
			counts[verdict] += part.counts[verdict] ?? 0
	}
	return { ...first, counts, agents: parts.flatMap(part => part.agents) }
}

export interface PreviewGroups {
	/** What the deletion will send: the deletable, plus the active elsewhere when included. */
	toDelete: UnhealthyAgentPreview[]
	/** Active on the other tool and not included: kept. */
	activeElsewhere: UnhealthyAgentPreview[]
	/** Seen recently, the Wazuh manager, not found: never deleted. */
	kept: UnhealthyAgentPreview[]
}

export function groupPreview(agents: UnhealthyAgentPreview[], includeActiveElsewhere: boolean): PreviewGroups {
	const groups: PreviewGroups = { toDelete: [], activeElsewhere: [], kept: [] }
	for (const agent of agents) {
		if (agent.verdict === "deletable") groups.toDelete.push(agent)
		else if (agent.verdict === "active_elsewhere")
			(includeActiveElsewhere ? groups.toDelete : groups.activeElsewhere).push(agent)
		else groups.kept.push(agent)
	}
	return groups
}

/** Why an agent is kept, in a few words, and a sentence for its title. */
export function verdictText(
	verdict: UnhealthyAgentVerdict,
	source: CustomerHealthcheckSource
): { label: string; hint: string } {
	const tool = toolName(source)
	const other = toolName(otherTool(source))
	switch (verdict) {
		case "deletable":
			return { label: "Delete", hint: `Neither ${tool} nor ${other} has seen it within the threshold.` }
		case "active_elsewhere":
			return {
				label: `Seen by ${other}`,
				hint: `${other} saw it within the threshold: the endpoint is likely still running. Deleting removes it from both.`
			}
		case "seen_recently":
			return { label: "Seen recently", hint: `${tool} saw it within the threshold.` }
		case "wazuh_manager":
			return { label: "Wazuh manager", hint: "The Wazuh manager's own agent is never deleted." }
		case "not_found":
			return { label: "Not found", hint: "It no longer exists, or it does not belong to this customer." }
	}
}

export interface DeletionTotals {
	requested: number
	deleted: number
	unconfirmed: number
	skipped: number
	failed: number
	/** Never sent: the run stopped, or a request failed, before their chunk. */
	notSent: number
}

export interface DeletionRun {
	totals: DeletionTotals
	results: UnhealthyAgentDeleteResult[]
	stopped: boolean
	error: unknown | null
}

/**
 * Send ``ids`` in chunks, one request at a time, and add up the answers. Stops before the next chunk
 * when ``shouldStop`` says so, and at the first request that fails (the backend reports per-agent
 * failures in a 200; a failed request means something wider is wrong): what was never sent is counted.
 */
export async function runChunkedDeletion(options: {
	ids: string[]
	chunkSize?: number
	send: (ids: string[]) => Promise<UnhealthyAgentsDeletion>
	onChunk?: (run: DeletionRun, processed: number) => void
	shouldStop?: () => boolean
}): Promise<DeletionRun> {
	const { ids, chunkSize = DELETE_CHUNK_SIZE, send, onChunk, shouldStop } = options
	const run: DeletionRun = {
		totals: { requested: ids.length, deleted: 0, unconfirmed: 0, skipped: 0, failed: 0, notSent: ids.length },
		results: [],
		stopped: false,
		error: null
	}
	let processed = 0
	for (const part of chunk(ids, chunkSize)) {
		if (shouldStop?.()) {
			run.stopped = true
			break
		}
		try {
			const answer = await send(part)
			run.results.push(...answer.results)
			run.totals.deleted += answer.deleted
			run.totals.unconfirmed += answer.unconfirmed
			run.totals.skipped += answer.skipped
			run.totals.failed += answer.failed
		} catch (error) {
			run.error = error
			break
		}
		processed += part.length
		run.totals.notSent = ids.length - processed
		onChunk?.(run, processed)
	}
	return run
}

/** The results worth a line after a run: failures first, then the unconfirmed, then the skipped. */
export function resultsToReview(results: UnhealthyAgentDeleteResult[]): UnhealthyAgentDeleteResult[] {
	const rank = (result: UnhealthyAgentDeleteResult) =>
		result.outcome === "failed" ? 0 : result.outcome === "deleted" && result.unconfirmed.length ? 1 : 2
	return results
		.filter(result => result.outcome !== "deleted" || result.unconfirmed.length)
		.sort((a, b) => rank(a) - rank(b))
}

/** How long ago, compact and plain: "<1h ago", "5h ago", "41d ago", "3y ago", "never". */
export function compactAge(lastSeen: string | null, now: number): string {
	if (!lastSeen) return "never"
	// Naive UTC from the API.
	const seen = Date.parse(lastSeen.endsWith("Z") || /[+-]\d\d:\d\d$/.test(lastSeen) ? lastSeen : `${lastSeen}Z`)
	if (Number.isNaN(seen)) return "—"
	// The sync stores Wazuh's "Unknown" as the epoch.
	if (seen <= 0) return "never"
	const hours = (now - seen) / 3_600_000
	if (hours < 0) return "in the future"
	if (hours < 1) return "<1h ago"
	if (hours < 48) return `${Math.floor(hours)}h ago`
	const days = hours / 24
	if (days < 730) return `${Math.floor(days)}d ago`
	return `${Math.floor(days / 365)}y ago`
}
