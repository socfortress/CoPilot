/**
 * Talon v2 action proposals in the chat (plan M5-11b; talon-analyst SPEC §5.3 M5-11, §9.5): pure
 * helpers. What a proposal's state means (final, holding the thread, how often to read it), its
 * labels, the provenance warnings, untrusted text made safe to look at (invisible and
 * direction-changing characters shown as escapes; a comment's links highlighted, their hosts in
 * punycode), CoPilot's times, and a thread's open calls.
 *
 * The shared records, the page's poll and the resume guard are in `actionCards.ts`. Every string a
 * proposal carries reaches the page as text, never as HTML or Markdown.
 *
 * Endpoint actions (talon-analyst's endpoint actions plan, EA-4): a collection's parameters as rows,
 * a command's shell, counts, shape and risk labels, and its lines cut into runs so tabs, trailing
 * spaces and characters nobody can see are shown (`commandSegments`).
 */
import type { TalonAction, TalonActionProvenance } from "@/types/talonActions"
import type { TalonV2ChatMessage, TalonV2ToolState } from "@/types/talonV2"

// ── states ───────────────────────────────────────────────────────────────────

/** talon-analyst's final statuses: its record can't change any more. */
export const TALON_FINAL = new Set(["executed", "failed", "denied", "expired", "withdrawn"])

/**
 * CoPilot states from which CoPilot moves the row no further, whatever talon-analyst's record says:
 * `refused` (the record changed, or talon-analyst refused the decision for everyone) and
 * `unreported` (the result couldn't be posted within its window).
 */
export const COPILOT_SETTLED = new Set(["refused", "unreported"])

/** CoPilot's naive UTC `DATETIME` (no offset) as a time; one with an offset as it says. Null if unreadable. */
export function parseUtc(value: string | null | undefined): Date | null {
	if (!value) return null
	const withZone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
	const date = new Date(withZone)
	return Number.isNaN(date.getTime()) ? null : date
}

/**
 * The thread waits on it: talon-analyst answers the thread's turns 409 while a record is `pending`,
 * or `approved` and still inside its result window (`result_due_by`; SPEC §9.5 "A turn while one
 * waits"). Past the window an approved record no longer holds the thread.
 */
export function blocksThread(action: TalonAction, now: number = Date.now()): boolean {
	if (TALON_FINAL.has(action.talon_status)) return false
	if (action.talon_status === "approved") {
		const due = parseUtc(action.result_due_by)
		if (due && now >= due.getTime()) return false
	}
	return true
}

/**
 * How the page's poll treats a proposal: `final`, nothing more can change; `slow`, CoPilot moves it
 * no further but talon-analyst's record isn't final (read now and then, so the thread heals);
 * `active`, it may change any moment.
 */
export function pollClass(action: TalonAction, now: number = Date.now()): "final" | "slow" | "active" {
	if (!blocksThread(action, now)) return "final"
	return COPILOT_SETTLED.has(action.state) ? "slow" : "active"
}

/** May still be withdrawn by its requester. */
export function isWithdrawable(action: TalonAction): boolean {
	return action.is_requester && action.state === "pending" && action.talon_status === "pending" && !action.expired
}

/** The actions whose target is a host (`{customer_code, agent_id, velociraptor_id, hostname}`). */
const HOST_ACTIONS = new Set(["quarantine_host", "release_host", "collect_artifact", "endpoint_command"])

export function isHostAction(action: Pick<TalonAction, "action">): boolean {
	return HOST_ACTIONS.has(action.action)
}

const ACTION_LABELS: Record<string, string> = {
	set_alert_status: "Set the alert's status",
	assign_alert: "Assign the alert",
	comment_on_alert: "Comment on the alert",
	quarantine_host: "Quarantine the host",
	release_host: "Release the host from quarantine",
	collect_artifact: "Collect a Velociraptor artifact",
	endpoint_command: "Run a command on the endpoint"
}

export function actionLabel(action: string): string {
	return ACTION_LABELS[action] ?? action
}

/**
 * An endpoint action's kind for a list row: a collection with its artifact (untrusted text), a
 * command with its shell (CoPilot's own name for the artifact); null for any other action.
 */
export function endpointKind(
	action: Pick<TalonAction, "action" | "args">
): { kind: "collection" | "command"; label: string; detail: string } | null {
	const artifact = action.args?.artifact_name
	const artifactText = typeof artifact === "string" ? artifact : ""
	if (action.action === "collect_artifact") return { kind: "collection", label: "Collection", detail: artifactText }
	if (action.action === "endpoint_command") {
		return { kind: "command", label: "Command", detail: shellOf(artifact) ?? artifactText }
	}
	return null
}

const STATE_LABELS: Record<string, string> = {
	pending: "Waiting for a decision",
	claiming: "Being decided",
	claimed: "Approved, about to run",
	executing: "Running",
	executed: "Executed",
	failed: "Failed",
	denied: "Denied",
	expired: "Expired",
	withdrawn: "Withdrawn",
	refused: "Can no longer be decided",
	claim_lost: "Not run: the approval's answer was lost",
	unreported: "Run, but the outcome wasn't reported to Talon"
}

/** CoPilot's state of the proposal, in words. */
export function stateLabel(action: Pick<TalonAction, "state" | "expired">): string {
	if (action.state === "pending" && action.expired) return STATE_LABELS.expired
	return STATE_LABELS[action.state] ?? action.state
}

export type StateTone = "waiting" | "running" | "success" | "error" | "neutral"

export function stateTone(action: Pick<TalonAction, "state" | "expired">): StateTone {
	if (action.state === "pending") return action.expired ? "neutral" : "waiting"
	if (["claiming", "claimed", "executing"].includes(action.state)) return "running"
	if (action.state === "executed") return "success"
	if (["failed", "claim_lost", "refused", "unreported"].includes(action.state)) return "error"
	return "neutral"
}

// ── provenance ───────────────────────────────────────────────────────────────

export interface ProvenanceWarning {
	flag: "injection_detected" | "untrusted_seen" | "web_used" | "endpoint_output_used" | "copied_from_output"
	severity: "error" | "warning"
	text: string
}

export const PROVENANCE_INJECTION =
	"Talon's injection defender flagged text read in the turn that proposed this. Check the proposal against the alert or host yourself before approving."
export const PROVENANCE_UNTRUSTED =
	"Earlier in this thread Talon read text the injection defender flagged. The proposal may have been steered by it."
export const PROVENANCE_WEB = "This thread used text from the web. The proposal may have been shaped by it."
export const PROVENANCE_ENDPOINT_OUTPUT =
	"This proposal was made after reading endpoint output. Text on the host may have steered it."
export const PROVENANCE_COPIED =
	"Parts of this command were copied from endpoint output. Read those parts closely: text on the host may have written them."

export function provenanceWarnings(provenance: TalonActionProvenance | null | undefined): ProvenanceWarning[] {
	const p = provenance ?? {}
	const out: ProvenanceWarning[] = []
	if (p.injection_detected === true) {
		out.push({ flag: "injection_detected", severity: "error", text: PROVENANCE_INJECTION })
	}
	if (p.untrusted_seen === true) out.push({ flag: "untrusted_seen", severity: "warning", text: PROVENANCE_UNTRUSTED })
	if (p.web_used === true) out.push({ flag: "web_used", severity: "warning", text: PROVENANCE_WEB })
	if (p.copied_from_output === true) {
		out.push({ flag: "copied_from_output", severity: "error", text: PROVENANCE_COPIED })
	}
	if (p.endpoint_output_used === true) {
		out.push({ flag: "endpoint_output_used", severity: "warning", text: PROVENANCE_ENDPOINT_OUTPUT })
	}
	return out
}

// ── endpoint actions: collections and commands ───────────────────────────────

/** talon-analyst's risk labels (`talon.endpoint_commands.RISK_PATTERNS`), in words. */
const RISK_LABELS: Record<string, string> = {
	network_fetch: "Network fetch",
	delete_or_kill: "Deletes or kills",
	registry_or_service: "Registry or service change",
	account_change: "Account change",
	persistence: "Persistence",
	shutdown_or_reboot: "Shutdown or reboot"
}

export const RISK_LABELS_NOTE =
	"Risk labels are heuristics talon-analyst's code computes from the command's text: they inform, they don't refuse, and a command can do harm without any."

export interface RiskLabel {
	/** The label as the record holds it (untrusted text when it isn't one talon-analyst defines). */
	key: string
	text: string
	known: boolean
}

/** A command's risk labels from `provenance.risk_labels`, in the record's order; only strings, each once. */
export function riskLabels(provenance: TalonActionProvenance | null | undefined): RiskLabel[] {
	const raw = provenance?.risk_labels
	if (!Array.isArray(raw)) return []
	const out: RiskLabel[] = []
	const seen = new Set<string>()
	for (const label of raw) {
		if (typeof label !== "string" || seen.has(label)) continue
		seen.add(label)
		const known = Object.hasOwn(RISK_LABELS, label)
		out.push({ key: label, text: known ? RISK_LABELS[label] : label, known })
	}
	return out
}

export type CommandShape = "read-only" | "free-form" | "unknown"

/**
 * A command's shape (`provenance.shape`): `read-only` only when the record says exactly that;
 * `free-form` when it says so; anything else (missing, another value) is `unknown`, shown with the
 * same caution as free-form, never as read-only.
 */
export function commandShape(provenance: TalonActionProvenance | null | undefined): CommandShape {
	const shape = provenance?.shape
	if (shape === "read-only" || shape === "free-form") return shape
	return "unknown"
}

/** The shell CoPilot's command artifact runs (`CommandArtifactsEnum`); null for any other artifact. */
export function shellOf(artifact: unknown): string | null {
	switch (artifact) {
		case "Windows.System.PowerShell":
			return "PowerShell"
		case "Linux.Sys.BashShell":
			return "bash"
		case "Windows.System.CmdShell":
			return "cmd"
		default:
			return null
	}
}

/**
 * A command's size as talon-analyst measures it (`check_command`): characters are code points, and
 * lines are counted without the newlines that end the command.
 */
export function commandCounts(command: string): { lines: number; chars: number } {
	return { lines: command.replace(/\n+$/, "").split("\n").length, chars: [...command].length }
}

/** "1 line, 12 characters" / "40 lines, 1,203 characters". */
export function countsText(command: string): string {
	const { lines, chars } = commandCounts(command)
	return `${lines} ${lines === 1 ? "line" : "lines"}, ${chars.toLocaleString("en-US")} ${chars === 1 ? "character" : "characters"}`
}

/**
 * The command's first line that isn't blank (only spaces and tabs), as written, with its number
 * (from 1). A command of blank lines only gives its first line.
 */
export function firstContentLine(command: string): { line: number; text: string } {
	const lines = command.split("\n")
	const index = lines.findIndex(line => !/^[\t\p{Zs}]*$/u.test(line))
	return index < 0 ? { line: 1, text: lines[0] ?? "" } : { line: index + 1, text: lines[index] }
}

export type CommandSegment =
	/** Printable ASCII, and runs of fewer than four spaces inside a line. */
	| { kind: "text"; text: string }
	/** Visible characters outside ASCII, highlighted: a look-alike letter can hide among them. */
	| { kind: "nonascii"; text: string; trailing?: boolean }
	/** A tab, kept as the tab itself and marked. */
	| { kind: "tab"; text: string; trailing?: boolean }
	/** Fewer than four spaces that end a line, kept as written and highlighted. */
	| { kind: "trailing"; text: string }
	/** Four or more spaces in a row, shown as `⟨␠×N⟩`; `trailing` when they end the line. */
	| { kind: "spaces"; text: string; count: number; trailing: boolean }
	/** A space where a row wraps (the last of a row or the first of the next), drawn as `␠`. */
	| { kind: "edge"; text: string }
	/** A character nobody can see, shown as `⟨U+000D⟩`; `trailing` when it ends the line. */
	| { kind: "escape"; text: string; char: string; trailing?: boolean }

/**
 * Characters a reader can't see or can't tell from a space: format (Cf), control (Cc) but tab and
 * newline, surrogates, the line and paragraph separators, every space separator (Zs) but U+0020,
 * every default-ignorable code point (variation selectors, Hangul fillers…), and U+2800 (the
 * braille blank).
 */
const UNSEEN_CHAR = /[\p{Cf}\p{Cs}\p{Zl}\p{Zp}\p{Default_Ignorable_Code_Point}\u2800]|(?![\t\n])\p{Cc}|(?! )\p{Zs}/u
const UNSEEN_ANY = new RegExp(UNSEEN_CHAR.source, "u")

/** The text holds a character nobody can see (talon-analyst refuses those in a command). */
export function hasUnseenChars(text: string): boolean {
	return UNSEEN_ANY.test(text)
}

/** Spaces in a row from this many on are shown as `⟨␠×N⟩`, so a long gap can't push text away. */
export const SPACES_RUN = 4

type CharClass = "tab" | "space" | "unseen" | "nonascii" | "ascii"

function classOf(char: string): CharClass {
	if (char === "\t") return "tab"
	if (char === " ") return "space"
	if (UNSEEN_CHAR.test(char)) return "unseen"
	return /[^\x20-\x7E]/.test(char) ? "nonascii" : "ascii"
}

/** One line (no `\n`) as runs; the whitespace that ends it (tabs and every Zs) is marked trailing. */
function lineSegments(line: string): CommandSegment[] {
	const tail = /[\t\p{Zs}]+$/u.exec(line)
	const trailingFrom = tail ? tail.index : line.length
	const out: CommandSegment[] = []
	const push = (segment: CommandSegment) => {
		const last = out.at(-1)
		if (segment.kind === "text" && last?.kind === "text") last.text += segment.text
		else out.push(segment)
	}
	const flush = (cls: CharClass, text: string, trailing: boolean) => {
		if (!text) return
		if (cls === "space") {
			const count = text.length
			if (count >= SPACES_RUN) push({ kind: "spaces", text: `⟨␠×${count}⟩`, count, trailing })
			else push(trailing ? { kind: "trailing", text } : { kind: "text", text })
		} else if (cls === "nonascii") {
			push(trailing ? { kind: "nonascii", text, trailing } : { kind: "nonascii", text })
		} else {
			push({ kind: "text", text })
		}
	}
	let run = ""
	let runClass: CharClass | null = null
	let runTrailing = false
	let index = 0
	for (const char of line) {
		const cls = classOf(char)
		const trailing = index >= trailingFrom
		index += char.length
		if (cls === "tab" || cls === "unseen") {
			if (runClass) flush(runClass, run, runTrailing)
			run = ""
			runClass = null
			if (cls === "tab") {
				push(trailing ? { kind: "tab", text: "\t", trailing } : { kind: "tab", text: "\t" })
			} else {
				const escape = { kind: "escape" as const, text: escapeOf(char), char }
				push(trailing ? { ...escape, trailing } : escape)
			}
			continue
		}
		if (cls !== runClass || trailing !== runTrailing) {
			if (runClass) flush(runClass, run, runTrailing)
			run = ""
			runClass = cls
			runTrailing = trailing
		}
		run += char
	}
	if (runClass) flush(runClass, run, runTrailing)
	return out
}

/**
 * A command's lines, each as runs: plain text, non-ASCII runs, tabs, spaces (four or more as
 * `⟨␠×N⟩`), the whitespace that ends a line, and escapes for characters nobody can see. Joined,
 * the runs' texts are the command but for those escapes and `⟨␠×N⟩` marks; lines are joined by `\n`.
 */
export function commandSegments(command: string): CommandSegment[][] {
	return command.split("\n").map(lineSegments)
}

/** Columns a box wraps a command line at, at most, so nothing hides beyond its right edge. */
export const WRAP_COLUMNS = 72
/** The fewest columns a box wraps at, however narrow it is (it then scrolls sideways, and says so). */
export const MIN_WRAP_COLUMNS = 16
const TAB_STOP = 4
// Characters a monospace font draws two columns wide: East Asian wide and fullwidth, and emoji.
const WIDE =
	/[\u1100-\u115F\u2E80-\u303E\u3041-\u33FF\u3400-\u4DBF\u4E00-\u9FFF\uA000-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE4F\uFF00-\uFF60\uFFE0-\uFFE6\u{1F300}-\u{1F64F}\u{1F900}-\u{1F9FF}\u{20000}-\u{3FFFD}]/u

function charsOf(text: string): string[] {
	return Array.from(text)
}

/** Columns one character takes in a monospace font. */
export function charColumns(char: string): number {
	return WIDE.test(char) ? 2 : 1
}

function textColumns(text: string): number {
	return charsOf(text).reduce((sum, char) => sum + charColumns(char), 0)
}

/** Columns a run takes starting at column `col` (a tab to its next stop). */
export function segmentColumns(segment: CommandSegment, col = 0): number {
	return segment.kind === "tab" ? TAB_STOP - (col % TAB_STOP) : textColumns(segment.text)
}

/**
 * One line's runs cut into rows of at most `columns` columns (a tab to its next stop, a wide
 * character two; an escape or a `⟨␠×N⟩` mark is never cut). Every row after the first continues the
 * line. A space where a row wraps (the last of a row, or the first of the next) would look like no
 * space at all, so it is drawn as `␠` (an `edge` run).
 */
export function wrapSegments(segments: CommandSegment[], columns: number = WRAP_COLUMNS): CommandSegment[][] {
	const width = Math.max(1, Math.floor(columns))
	const rows: CommandSegment[][] = [[]]
	let col = 0
	const newRow = () => {
		rows.push([])
		col = 0
	}
	for (const segment of segments) {
		if (segment.kind === "text" || segment.kind === "nonascii" || segment.kind === "trailing") {
			let piece = ""
			for (const char of charsOf(segment.text)) {
				const w = charColumns(char)
				if (col > 0 && col + w > width) {
					if (piece) rows[rows.length - 1].push({ ...segment, text: piece })
					piece = ""
					newRow()
				}
				piece += char
				col += w
			}
			if (piece) rows[rows.length - 1].push({ ...segment, text: piece })
			continue
		}
		let w = segmentColumns(segment, col)
		if (col > 0 && col + w > width) {
			newRow()
			w = segmentColumns(segment, 0)
		}
		rows[rows.length - 1].push(segment)
		col += w
	}
	// The spaces at each wrap, drawn: the last run of a row and the first of the next.
	for (let i = 0; i < rows.length - 1; i++) {
		markEdge(rows[i], "end")
		markEdge(rows[i + 1], "start")
	}
	return rows
}

function markEdge(row: CommandSegment[], side: "start" | "end") {
	const index = side === "start" ? 0 : row.length - 1
	const segment = row[index]
	if (!segment || segment.kind !== "text") return
	const text = segment.text
	if (side === "end" && text.endsWith(" ")) {
		const rest = text.slice(0, -1)
		row.splice(index, 1, ...(rest ? [{ ...segment, text: rest }] : []), { kind: "edge", text: "␠" })
	} else if (side === "start" && text.startsWith(" ")) {
		const rest = text.slice(1)
		row.splice(index, 1, { kind: "edge", text: "␠" }, ...(rest ? [{ ...segment, text: rest }] : []))
	}
}

/** How many tabs, and how many lines end in whitespace (tabs and every Zs): named beside the command. */
export function whitespaceCounts(command: string): { tabs: number; trailingLines: number; spaceRuns: number } {
	return {
		tabs: (command.match(/\t/g) ?? []).length,
		trailingLines: command.split("\n").filter(line => /[\t\p{Zs}]$/u.test(line)).length,
		spaceRuns: (command.match(new RegExp(` {${SPACES_RUN},}`, "g")) ?? []).length
	}
}

// ── look-alike characters ─────────────────────────────────────────────────────

const SCRIPTS: [string, RegExp][] = [
	["Latin", /\p{Script=Latin}/u],
	["Greek", /\p{Script=Greek}/u],
	["Cyrillic", /\p{Script=Cyrillic}/u],
	["Armenian", /\p{Script=Armenian}/u],
	["Georgian", /\p{Script=Georgian}/u],
	["Cherokee", /\p{Script=Cherokee}/u],
	["Coptic", /\p{Script=Coptic}/u],
	["Hebrew", /\p{Script=Hebrew}/u],
	["Arabic", /\p{Script=Arabic}/u],
	["Han", /\p{Script=Han}/u],
	["Hiragana", /\p{Script=Hiragana}/u],
	["Katakana", /\p{Script=Katakana}/u],
	["Hangul", /\p{Script=Hangul}/u]
]
// Right-to-left characters by code point: Hebrew to Arabic Extended (U+0590-08FF), the Hebrew and
// Arabic presentation forms (FB1D-FDFF, FE70-FEFF), and the right-to-left blocks of planes 1
// (10800-10FFF, 1E800-1EFFF). Ranges, not script names, so a script newer than the browser counts.
const RTL = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF\u{10800}-\u{10FFF}\u{1E800}-\u{1EFFF}]/u

export interface Lookalikes {
	/** Code points outside ASCII. */
	nonAscii: number
	/** The scripts of its letters, in `SCRIPTS` order, "another script" last. */
	scripts: string[]
	/** It holds characters of a right-to-left script. */
	rtl: boolean
}

export function lookalikes(text: string): Lookalikes {
	let nonAscii = 0
	let rtl = false
	const found = new Set<string>()
	for (const char of text) {
		if ((char.codePointAt(0) ?? 0) > 127) nonAscii++
		if (RTL.test(char)) rtl = true
		if (!/\p{L}/u.test(char)) continue
		const script = SCRIPTS.find(([, pattern]) => pattern.test(char))
		found.add(script ? script[0] : "another script")
	}
	const order = [...SCRIPTS.map(([name]) => name), "another script"]
	return { nonAscii, scripts: order.filter(name => found.has(name)), rtl }
}

export interface LookalikeWarning {
	flag: "non_ascii" | "mixed_scripts" | "rtl"
	text: string
}

/** What a command or a parameter value holds that can make it read as something it isn't. */
export function lookalikeWarnings(text: string, what = "This command"): LookalikeWarning[] {
	const found = lookalikes(text)
	const out: LookalikeWarning[] = []
	if (found.nonAscii) {
		out.push({
			flag: "non_ascii",
			text: `${what} holds ${found.nonAscii} non-ASCII ${found.nonAscii === 1 ? "character" : "characters"}, highlighted: a look-alike letter can make it read as something it isn't.`
		})
	}
	if (found.scripts.length > 1) {
		out.push({
			flag: "mixed_scripts",
			text: `${what} mixes scripts (${found.scripts.join(", ")}): letters of different alphabets can look the same.`
		})
	}
	if (found.rtl) {
		out.push({
			flag: "rtl",
			text: `${what} holds right-to-left characters: they can change the order it is drawn in.`
		})
	}
	return out
}

/** The OS a command artifact's shell runs on, as `target.os` names it; null for an unknown shell. */
export function shellOs(artifact: unknown): "windows" | "linux" | null {
	if (artifact === "Windows.System.PowerShell" || artifact === "Windows.System.CmdShell") return "windows"
	if (artifact === "Linux.Sys.BashShell") return "linux"
	return null
}

/** Whether the record lists risk labels at all (a list, even empty), as against not labelling them. */
export function riskLabelled(provenance: TalonActionProvenance | null | undefined): boolean {
	return Array.isArray(provenance?.risk_labels)
}

export interface ParameterRow {
	key: string
	value: string
}

/**
 * A collection's parameters, as CoPilot sends them to Velociraptor (`{env: [{key, value}]}`), one
 * row each, in the record's order. `ok` is false when the record holds them in another shape: the
 * card then shows them raw.
 */
export function collectionParameters(parameters: unknown): { ok: boolean; rows: ParameterRow[] } {
	if (parameters === undefined || parameters === null) return { ok: true, rows: [] }
	if (typeof parameters !== "object" || Array.isArray(parameters)) return { ok: false, rows: [] }
	const keys = Object.keys(parameters)
	const env = (parameters as { env?: unknown }).env
	if (keys.length !== 1 || keys[0] !== "env" || !Array.isArray(env)) return { ok: false, rows: [] }
	const rows: ParameterRow[] = []
	for (const item of env) {
		if (!item || typeof item !== "object" || Array.isArray(item)) return { ok: false, rows: [] }
		const { key, value } = item as { key?: unknown; value?: unknown }
		if (typeof key !== "string" || Object.keys(item).some(k => k !== "key" && k !== "value")) {
			return { ok: false, rows: [] }
		}
		rows.push({ key, value: typeof value === "string" ? value : (JSON.stringify(value) ?? String(value)) })
	}
	return { ok: true, rows }
}

// ── untrusted text ───────────────────────────────────────────────────────────

/**
 * Characters that are invisible or change the direction text is drawn in: every format character
 * (Cf: zero-width spaces and joiners, bidi embeddings, overrides and isolates, the BOM, the Arabic
 * letter mark, the Mongolian vowel separator, soft hyphens, tags…). Untrusted text shows them as `⟨U+202E⟩`, so a
 * right-to-left override can't make `evil.invalid/\u202Emoc.tfosorcim` read as `microsoft.com`.
 */
const HIDDEN = /\p{Cf}/u
const HIDDEN_ALL = /\p{Cf}/gu

export const HIDDEN_CHARS_WARNING =
	"This proposal holds invisible or direction-changing characters, shown as ⟨U+…⟩: its text may not read the way it looks."

export function hasHiddenChars(text: string | null | undefined): boolean {
	return !!text && HIDDEN.test(text)
}

/** `⟨U+202E⟩` for one hidden character. */
export function escapeOf(char: string): string {
	return `⟨U+${(char.codePointAt(0) ?? 0).toString(16).toUpperCase().padStart(4, "0")}⟩`
}

export type TextSegment =
	| { kind: "text"; text: string }
	/** A hidden character, shown as its escape; `char` is the character itself. */
	| { kind: "escape"; text: string; char: string }
	/** A link, highlighted and never clickable; `text` is how it is shown (its host in punycode). */
	| { kind: "link"; text: string; raw: string; punycode: boolean }

/** `text` as plain runs and escapes for its hidden characters. */
export function safeSegments(text: string): TextSegment[] {
	const out: TextSegment[] = []
	let last = 0
	for (const match of text.matchAll(HIDDEN_ALL)) {
		const start = match.index ?? 0
		if (start > last) out.push({ kind: "text", text: text.slice(last, start) })
		out.push({ kind: "escape", text: escapeOf(match[0]), char: match[0] })
		last = start + match[0].length
	}
	if (last < text.length) out.push({ kind: "text", text: text.slice(last) })
	return out
}

/**
 * What a comment shows as a link: a scheme (`https://`, `hxxp://`, `ftp://`…), `www.`, or a host
 * name followed by a path, broadly as talon-analyst sets `links` (`talon.tools.actions._LINK`).
 * A link never holds a hidden character: it ends at one, and the character is shown escaped.
 */
const NOT_IN_LINK = String.raw`[^\s<>"'\x60\p{Cf}]`
const LINK = new RegExp(
	String.raw`(?:\b[a-z][a-z0-9+.-]*:\/\/|\bwww\.)${NOT_IN_LINK}+|\b[\p{L}\p{N}_-]+(?:\.[\p{L}\p{N}_-]+)+\/${NOT_IN_LINK}*`,
	"giu"
)
const TRAILING = /[.,;:!?)\]}]+$/
// eslint-disable-next-line no-control-regex
const NON_ASCII = /[^\x00-\x7F]/

/** A link with its host in punycode (`xn--…`), as a browser would resolve it; as it is if it can't be. */
export function punycodeLink(link: string): { text: string; punycode: boolean } {
	const schemeEnd = link.indexOf("://")
	const start = schemeEnd > 0 && /^[a-z][a-z0-9+.-]*$/i.test(link.slice(0, schemeEnd)) ? schemeEnd + 3 : 0
	const after = link.slice(start)
	const stop = after.search(/[/?#]/)
	const authority = stop < 0 ? after : after.slice(0, stop)
	const rest = stop < 0 ? "" : after.slice(stop)
	const at = authority.lastIndexOf("@")
	const userinfo = authority.slice(0, at + 1)
	const hostport = authority.slice(at + 1)
	if (!NON_ASCII.test(hostport)) return { text: link, punycode: false }
	try {
		const host = new URL(`http://${hostport}`).host
		return { text: `${link.slice(0, start)}${userinfo}${host}${rest}`, punycode: host !== hostport }
	} catch {
		return { text: link, punycode: false }
	}
}

/** A comment: plain runs, escapes for hidden characters, and its links (hosts in punycode). */
export function linkSegments(text: string): TextSegment[] {
	const out: TextSegment[] = []
	let last = 0
	for (const match of text.matchAll(LINK)) {
		const start = match.index ?? 0
		// Punctuation that ends a sentence or closes a bracket isn't part of the link.
		const raw = match[0].replace(TRAILING, "")
		if (!raw) continue
		if (start > last) out.push(...safeSegments(text.slice(last, start)))
		const shown = punycodeLink(raw)
		out.push({ kind: "link", text: shown.text, raw, punycode: shown.punycode })
		last = start + raw.length
	}
	if (last < text.length) out.push(...safeSegments(text.slice(last)))
	return out
}

// ── times ────────────────────────────────────────────────────────────────────

/** "3h 59m", "4m 10s", "12s": the time left until `until` (ms); null once it has passed. */
export function timeLeft(until: number | null, now: number): string | null {
	if (until === null) return null
	const seconds = Math.floor((until - now) / 1000)
	if (seconds <= 0) return null
	const h = Math.floor(seconds / 3600)
	const m = Math.floor((seconds % 3600) / 60)
	const s = seconds % 60
	if (h) return `${h}h ${m}m`
	if (m) return `${m}m ${s}s`
	return `${s}s`
}

/**
 * When a pending proposal expires, by this browser's clock: CoPilot's `expires_in_seconds` counted
 * from when its answer arrived (so a skewed clock doesn't move it), else `expires_at`; null if
 * neither can be read.
 */
export function expiryDeadline(action: TalonAction, receivedAt: number): number | null {
	if (typeof action.expires_in_seconds === "number" && Number.isFinite(action.expires_in_seconds)) {
		return receivedAt + action.expires_in_seconds * 1000
	}
	return parseUtc(action.expires_at)?.getTime() ?? null
}

// ── a thread's open calls ────────────────────────────────────────────────────

const ANSWERED = new Set<TalonV2ToolState>(["output-available", "output-error", "output-denied"])

export interface OpenApproval {
	approvalId: string
	toolCallId: string
	/** The stream's or the read-back's status of the card: a hint until the card has read the record. */
	hint: string
}

/**
 * The approval cards of a thread whose calls no later turn has answered yet, in order. A resumed
 * call's answer comes in the turn that resumed it, by the same call id and without a card (SPEC §8
 * "Reading turns back"), so a card followed by its answer is closed.
 */
export function openApprovals(messages: TalonV2ChatMessage[]): OpenApproval[] {
	const open = new Map<string, OpenApproval>()
	for (const message of messages) {
		if (message.role !== "assistant") continue
		for (const item of message.items) {
			if (item.kind !== "tool") continue
			if (item.approval) {
				open.set(item.toolCallId, {
					approvalId: item.approval.id,
					toolCallId: item.toolCallId,
					hint: item.approval.status
				})
			} else if (ANSWERED.has(item.state)) {
				open.delete(item.toolCallId)
			}
		}
	}
	return [...open.values()]
}
