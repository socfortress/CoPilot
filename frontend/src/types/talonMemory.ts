// The Talon Memory tab's payloads, as CoPilot relays them (`backend/app/connectors/talon/schema/talon_memory.py`).
// Every talon-analyst field may be null: CoPilot drops what it can't read rather than failing.

export type TalonMemoryRoom = "alerts" | "false_positives" | "threat_intel" | "assets" | "environment" | "other"
export type TalonMemorySource = "investigation" | "review_durable" | "review_one_off" | "chat_remember" | "other"

export interface TalonMemoryStats {
	success: boolean
	customer_code: string
	total: number | null
	checked_at: string | null
	rooms: Record<TalonMemoryRoom, number | null>
	sources: Record<TalonMemorySource, number | null>
	testing_hidden: number | null
	growth: { date: string; filed: number | null }[]
	/** False: Talon hit a cap while counting, so the figures are approximate. */
	complete?: boolean | null
}

export interface TalonMemorySourceRef {
	job_id: string | null
	alert_id: number | null
}

export interface TalonMemoryItem {
	drawer_id: string
	/** The id fits CoPilot's safe pattern: it can be opened and forgotten. */
	openable: boolean
	room: TalonMemoryRoom
	/** The room as Talon wrote it: a wing may hold rooms outside the five (`room` is then "other"). */
	room_name?: string | null
	source: TalonMemorySource
	source_ref: TalonMemorySourceRef | null
	filed_at: string | null
	durable: boolean | null
	testing_hidden: boolean | null
	visible_to_investigations: boolean | null
	preview: string | null
}

export interface TalonMemoryPage {
	success: boolean
	items: TalonMemoryItem[]
	next_cursor: string | null
}

export interface TalonMemoryDrawer extends TalonMemoryItem {
	/** Markdown, already de-anonymized for the customer by Talon. */
	content: string | null
	forgettable: boolean
	why_not_forgettable: string | null
	why_hidden: string | null
}

export interface TalonMemoryAsset {
	asset: string
	openable: boolean
	alerts: number | null
	iocs: number | null
	last_seen: string | null
}

export interface TalonMemoryFact {
	subject: string | null
	predicate: string | null
	object: string | null
	valid_from: string | null
	valid_to: string | null
}

export interface TalonMemoryTimeline {
	success: boolean
	asset: string
	facts: TalonMemoryFact[]
}

export interface TalonChatMemoryItem {
	drawer_id: string
	openable: boolean
	filed_at: string | null
	preview: string | null
	thread_id: string | null
}

export interface TalonMemoryQuery {
	room?: TalonMemoryRoom | null
	source?: TalonMemorySource | null
	q?: string | null
	since?: string | null
	before?: string | null
	limit?: number
	cursor?: string | null
}
