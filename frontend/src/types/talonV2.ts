/**
 * Talon v2 chat (talon-analyst SPEC §8 "v2 API", FR-CHAT-7; CoPilot's proxy under `/api/talon/v2`).
 *
 * Wire shapes first (what talon-analyst sends, through CoPilot's proxy), then the one UI model both
 * the live stream and the read-back are folded into, so a turn renders the same way either path.
 */

// ── threads ──────────────────────────────────────────────────────────────────

export interface TalonV2Thread {
	id: string
	title: string | null
	/** null: a general thread, with no customer data (D39). */
	customer_code: string | null
	/** `deleted` only in the answer to archiving a thread that never had a turn. */
	status: "active" | "archived" | "deleted" | string
	created_at: string | null
	updated_at: string | null
	archived_at: string | null
	/** false once the thread's customer is no longer the caller's: its turns are refused (D40). */
	accessible: boolean
	/** The post-compaction size of the last completed turn's last request (M5-5t); null before one. */
	context_tokens?: number | null
}

export type TalonV2ThreadStatusFilter = "active" | "archived" | "all"

export interface TalonV2ThreadPage {
	threads: TalonV2Thread[]
	next: string | null
}

export interface TalonV2ThreadCreate {
	title?: string | null
	customer_code?: string | null
}

// ── the read-back (`GET /talon/v2/threads/{id}/messages`, M5-5t) ─────────────

export interface TalonV2Approval {
	/** The `action_request` id; CoPilot decides only from `GET /v2/actions/{id}` (M5-11), never from this. */
	id: string
	status: string
	approved?: boolean
}

export interface TalonV2UITextPart {
	type: "text"
	text: string
	state?: string
}

export interface TalonV2UIToolPart {
	/** `tool-<name>`; the name as talon-analyst shows it (`unknown_tool` for one it won't show). */
	type: string
	toolCallId: string
	state: string
	input?: unknown
	output?: unknown
	errorText?: string
	approval?: TalonV2Approval
	providerExecuted?: boolean
}

export type TalonV2UIPart = TalonV2UITextPart | TalonV2UIToolPart | { type: string; [key: string]: unknown }

export interface TalonV2UIMessage {
	id: string
	role: "user" | "assistant" | string
	parts: TalonV2UIPart[]
	metadata?: {
		created_at?: string | null
		status?: "completed" | "failed" | "cut_off" | string
		error_text?: string
	}
}

export interface TalonV2MessagesPage {
	thread: TalonV2Thread
	messages: TalonV2UIMessage[]
	/** The cursor for the older turns, or null. */
	next: string | null
}

// ── the stream (`POST /talon/v2/chat/{id}`, the Vercel AI UI message stream) ──

export interface TalonV2Usage {
	input_tokens?: number | null
	output_tokens?: number | null
	requests?: number | null
	tool_calls?: number | null
	context_tokens?: number | null
	/** A decimal string from the usage ledger, shown as it is; null without a run id. */
	cost_usd?: string | null
}

/** The chunks the v2 parser hands on; anything else on the wire is ignored. */
export type TalonV2Chunk =
	| { type: "start" }
	| { type: "start-step" }
	| { type: "finish-step" }
	| { type: "text-start"; id: string }
	| { type: "text-delta"; id: string; delta: string }
	| { type: "text-end"; id: string }
	| { type: "tool-input-start"; toolCallId: string; toolName: string }
	| { type: "tool-input-available"; toolCallId: string; toolName: string; input: unknown }
	| { type: "tool-input-error"; toolCallId: string; toolName: string; input: unknown; errorText: string }
	| { type: "tool-output-available"; toolCallId: string; output: unknown }
	| { type: "tool-output-error"; toolCallId: string; errorText: string }
	| { type: "tool-output-denied"; toolCallId: string }
	| { type: "tool-approval-request"; approvalId: string; toolCallId: string }
	| { type: "data-usage"; data: TalonV2Usage }
	| { type: "error"; errorText: string }
	| { type: "finish"; finishReason?: string }

// ── the UI model ─────────────────────────────────────────────────────────────

export type TalonV2ToolState =
	| "input-streaming"
	| "input-available"
	| "output-available"
	| "output-error"
	| "output-denied"
	| "approval-requested"
	| "approval-responded"

export interface TalonV2TextItem {
	kind: "text"
	id: string
	text: string
}

export interface TalonV2ToolItem {
	kind: "tool"
	toolCallId: string
	/** null: a resumed call's answer whose name this view never saw. */
	name: string | null
	state: TalonV2ToolState
	input?: unknown
	output?: unknown
	errorText?: string
	approval?: TalonV2Approval
}

export type TalonV2Item = TalonV2TextItem | TalonV2ToolItem

/** `streaming` while a reply arrives; the rest are talon-analyst's `metadata.status`. */
export type TalonV2TurnStatus = "streaming" | "completed" | "failed" | "cut_off"

export interface TalonV2ChatMessage {
	id: string
	role: "user" | "assistant"
	items: TalonV2Item[]
	createdAt: string | null
	status: TalonV2TurnStatus
	errorText?: string
	usage?: TalonV2Usage
}
