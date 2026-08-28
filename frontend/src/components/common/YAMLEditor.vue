<template>
	<codemirror
		v-model="code"
		:placeholder
		:autofocus
		:indent-with-tab="false"
		:tab-size
		:extensions
		:style="{
			height: '100%'
		}"
		@ready="handleReady"
	/>
</template>

<script setup lang="ts">
import type { Diagnostic } from "@codemirror/lint"
import type { EditorState as EditorStateT, Extension, Text } from "@codemirror/state"
import type { DecorationSet, EditorView as EditorViewT } from "@codemirror/view"
import { redo, redoDepth, undo, undoDepth } from "@codemirror/commands"
import { linter } from "@codemirror/lint"
import { Annotation, EditorState, StateEffect, StateField } from "@codemirror/state"
import { oneDark } from "@codemirror/theme-one-dark"
import { Decoration, EditorView } from "@codemirror/view"
import _isEqual from "lodash/isEqual"
import _trim from "lodash/trim"
import _uniqWith from "lodash/uniqWith"
import { tomorrow } from "thememirror"
import { computed, ref, shallowRef, watch } from "vue"
import { Codemirror } from "vue-codemirror"
import { useThemeStore } from "@/stores/theme"

export interface YAMLEditorCtx {
	undo: () => void
	redo: () => void
	scrollToLine: (line: number) => void
	goToLine: (line: number) => void
	setContent: (text: string) => void
	canUndo: () => boolean
	canRedo: () => boolean
}

export interface YAMLError {
	line: number
	column: number
	message: string
	level: "error" | "warning"
}

/** Injected by the consumer: turns the document text into a flat list of findings. */
export type YAMLValidator = (text: string) => YAMLError[] | Promise<YAMLError[]>

const {
	placeholder = "Code goes here...",
	autofocus = false,
	tabSize = 2,
	lockedKeys = [],
	validator,
	extraExtensions = []
} = defineProps<{
	placeholder?: string
	autofocus?: boolean
	tabSize?: number
	/**
	 * Keys that must never be removed or renamed: their token is highlighted and any
	 * edit touching the `key:` itself is rejected — the value stays fully editable.
	 */
	lockedKeys?: string[]
	/** Optional linter — when omitted the editor performs no validation at all. */
	validator?: YAMLValidator
	/** Escape hatch for consumer-specific CodeMirror extensions. */
	extraExtensions?: Extension[]
}>()

const emit = defineEmits<{
	(e: "errors", value: YAMLError[]): void
	(e: "blocked", key: string): void
}>()

const code = defineModel<string>("code", { default: "" })

const themeStore = useThemeStore()
const isDark = computed<boolean>(() => themeStore.isThemeDark)

// --- locked keys: detection ------------------------------------------------

interface KeySpan {
	lineFrom: number
	keyFrom: number
	keyTo: number // end of the key WORD (for the coloured mark)
	protectedTo: number // end of the protected span (through the colon)
	key: string
}

const keyRegex = computed<RegExp | null>(() =>
	lockedKeys.length ? new RegExp(`^(\\s*)(${lockedKeys.join("|")})\\b\\s*:`) : null
)

function computeSpans(doc: Text): KeySpan[] {
	const regex = keyRegex.value

	if (!regex) {
		return []
	}

	const spans: KeySpan[] = []

	for (let i = 1; i <= doc.lines; i++) {
		const line = doc.line(i)
		const match = regex.exec(line.text)

		if (!match) {
			continue
		}

		const keyFrom = line.from + match[1].length
		const keyTo = keyFrom + match[2].length
		const colon = line.text.indexOf(":", match[1].length + match[2].length)

		spans.push({
			lineFrom: line.from,
			keyFrom,
			keyTo,
			protectedTo: line.from + (colon >= 0 ? colon + 1 : match[0].length),
			key: match[2]
		})
	}

	return spans
}

// --- locked keys: decorations (tint the whole line + colour the key token) ---

const lineDecoration = Decoration.line({ class: "cm-locked-line" })
const keyDecoration = Decoration.mark({ class: "cm-locked-key" })

function buildDecorations(doc: Text): DecorationSet {
	const ranges: ReturnType<typeof keyDecoration.range>[] = []

	for (const span of computeSpans(doc)) {
		ranges.push(lineDecoration.range(span.lineFrom))
		ranges.push(keyDecoration.range(span.keyFrom, span.keyTo))
	}

	return Decoration.set(ranges, true)
}

const lockedField = StateField.define<DecorationSet>({
	create: (state: EditorStateT) => buildDecorations(state.doc),
	update: (value, tr) => (tr.docChanged ? buildDecorations(tr.state.doc) : value),
	provide: f => EditorView.decorations.from(f)
})

// Marks transactions we dispatch ourselves (e.g. loading a template) so the
// locked-key guard lets them through wholesale.
const programmatic = Annotation.define<boolean>()

// --- locked keys: edit guard -----------------------------------------------
// Prevents REMOVING a locked key while allowing anything that keeps them all
// (value edits, and full-document template replacement).

let lastBlockAt = 0

const lockedGuard = EditorState.transactionFilter.of(tr => {
	if (!tr.docChanged) {
		return tr
	}

	// our own template loads bypass the lock
	if (tr.annotation(programmatic)) {
		return tr
	}

	// Which locked key spans does this change touch (delete/alter the key token)?
	const before = computeSpans(tr.startState.doc)
	const touched = new Set<string>()

	tr.changes.iterChangedRanges((fromA, toA) => {
		for (const span of before) {
			// overlap of the change [fromA,toA] with the protected span [keyFrom,protectedTo]
			if (fromA < span.protectedTo && toA > span.keyFrom) {
				touched.add(span.key)
			}
		}
	})

	// no key token touched (e.g. value edit) → allow
	if (touched.size === 0) {
		return tr
	}

	// A key token was touched. Allow it as long as EVERY locked key still exists
	// afterwards — so a template reload (which contains them all) goes through, while
	// deleting or renaming a locked key is rejected.
	const afterKeys = new Set(computeSpans(tr.newDoc).map(span => span.key))
	const missing = lockedKeys.filter(key => !afterKeys.has(key))

	if (missing.length === 0) {
		return tr
	}

	const now = Date.now()

	if (now - lastBlockAt > 1200) {
		lastBlockAt = now
		emit("blocked", missing[0])
	}

	// drop the transaction — the locked key stays put
	return []
})

// --- jump-to-line: transient flash of a target line -------------------------

const flashEffect = StateEffect.define<number | null>()
const flashDecoration = Decoration.line({ class: "cm-flash-line" })

const flashField = StateField.define<DecorationSet>({
	create: () => Decoration.none,
	update(value, tr) {
		value = value.map(tr.changes)

		for (const effect of tr.effects) {
			if (effect.is(flashEffect)) {
				if (effect.value === null) {
					value = Decoration.none
				} else {
					const line = Math.max(1, Math.min(effect.value, tr.state.doc.lines))
					value = Decoration.set([flashDecoration.range(tr.state.doc.line(line).from)])
				}
			}
		}

		return value
	},
	provide: f => EditorView.decorations.from(f)
})

const styling = EditorView.baseTheme({
	".cm-locked-line": { backgroundColor: "rgba(2,132,199,0.07)", borderLeft: "2px solid #0284c7" },
	".cm-locked-key": { color: "#0284c7", fontWeight: "600" },
	"&dark .cm-locked-line": { backgroundColor: "rgba(56,189,248,0.10)", borderLeft: "2px solid #38bdf8" },
	"&dark .cm-locked-key": { color: "#7dd3fc", fontWeight: "600" },
	".cm-flash-line": { animation: "cmFlash 1.3s ease-out" },
	"@keyframes cmFlash": {
		"0%": { backgroundColor: "rgba(245,158,11,0.45)" },
		"100%": { backgroundColor: "rgba(245,158,11,0)" }
	}
})

// --- validation ------------------------------------------------------------

function convertYAMLErrorsToDiagnostics(errors: YAMLError[], text: string): Diagnostic[] {
	const diagnostics: Diagnostic[] = []
	const lines = text.split("\n")

	emit(
		"errors",
		errors
			.map(o => ({ ...o, message: _trim(o.message) }))
			.filter(o => !!o.message)
			.sort((a, b) => a.line - b.line)
	)

	errors.forEach(error => {
		// Calculate position in text
		let from = 0
		for (let i = 0; i < error.line - 1; i++) {
			from += (lines[i]?.length ?? 0) + 1 // +1 for newline
		}
		from += error.column - 1

		// Find the end of the error (end of line or end of message)
		const lineText = lines[error.line - 1] || ""
		const to = from + Math.min(lineText.length - (error.column - 1), 50) // Limit to 50 characters

		diagnostics.push({
			from,
			to,
			severity: error.level,
			message: error.message
		})
	})

	return diagnostics
}

async function validateYAML(text: string): Promise<Diagnostic[]> {
	let errors: YAMLError[] = []

	try {
		errors = (await validator?.(text)) || []
	} catch (err) {
		console.error(err)
	}

	return convertYAMLErrorsToDiagnostics(_uniqWith(errors, _isEqual), text)
}

const extensions = computed(() => {
	const list: Extension[] = [styling, flashField, EditorView.lineWrapping]

	if (lockedKeys.length) {
		list.push(lockedField, lockedGuard)
	}

	if (isDark.value) {
		list.push(oneDark)
	} else {
		list.push(tomorrow)
	}

	if (validator) {
		list.push(
			linter(async view => {
				const text = view.state.doc.toString()

				if (!text.trim()) {
					return []
				}

				return await validateYAML(text)
			})
		)
	}

	list.push(...extraExtensions)

	return list
})

const cmView = shallowRef<EditorViewT | null>(null)
const canUndo = ref<boolean>(false)
const canRedo = ref<boolean>(false)

function updateHistoryState() {
	canUndo.value = cmView.value ? !!undoDepth(cmView.value.state) : false
	canRedo.value = cmView.value ? !!redoDepth(cmView.value.state) : false
}

function handleReady(payload: { view: EditorViewT; state: EditorStateT; container: HTMLDivElement }) {
	cmView.value = payload.view
}

function handleUndo() {
	if (cmView.value) {
		undo({
			state: cmView.value.state,
			dispatch: cmView.value.dispatch
		})
	}
}

function handleRedo() {
	if (cmView.value) {
		redo({
			state: cmView.value.state,
			dispatch: cmView.value.dispatch
		})
	}
}

/** Scroll a 1-based line into view. */
function scrollToLine(line: number) {
	if (cmView.value) {
		const view = cmView.value
		const lineInfo = view.state.doc.line(Math.max(1, Math.min(line, view.state.doc.lines)))
		view.dispatch({
			effects: EditorView.scrollIntoView(lineInfo.from, { y: "center" })
		})
	}
}

/** Scroll a 1-based line into view, move the cursor there, and flash it. */
function goToLine(line: number) {
	const view = cmView.value

	if (!view || !line) {
		return
	}

	const lineNumber = Math.max(1, Math.min(line, view.state.doc.lines))
	const position = view.state.doc.line(lineNumber).from

	view.dispatch({
		selection: { anchor: position },
		effects: [EditorView.scrollIntoView(position, { y: "center" }), flashEffect.of(lineNumber)]
	})
	view.focus()

	window.setTimeout(() => {
		cmView.value?.dispatch({ effects: flashEffect.of(null) })
	}, 1400)
}

/** Replace the whole document (used to load a fresh template) — always allowed. */
function setContent(text: string) {
	const view = cmView.value

	if (!view) {
		// editor not ready yet — fall back to the reactive model
		code.value = text
		return
	}

	view.dispatch({
		changes: { from: 0, to: view.state.doc.length, insert: text },
		annotations: [programmatic.of(true)]
	})
}

watch(code, () => {
	updateHistoryState()
})

defineExpose({
	undo: handleUndo,
	redo: handleRedo,
	scrollToLine,
	goToLine,
	setContent,
	canRedo: () => canRedo.value,
	canUndo: () => canUndo.value
})
</script>
