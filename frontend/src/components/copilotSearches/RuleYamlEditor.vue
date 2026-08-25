<template>
	<codemirror
		v-model="code"
		placeholder="Write a Graylog-only detection rule…"
		:indent-with-tab="false"
		:tab-size="2"
		:extensions="extensions"
		:style="{ height: '100%' }"
		@ready="handleReady"
	/>
</template>

<script setup lang="ts">
import type { Text } from "@codemirror/state"
import type { EditorState as EditorStateT, Extension } from "@codemirror/state"
import { Annotation, EditorState, StateEffect, StateField } from "@codemirror/state"
import type { DecorationSet } from "@codemirror/view"
import { Decoration, EditorView } from "@codemirror/view"
import { oneDark } from "@codemirror/theme-one-dark"
import { tomorrow } from "thememirror"
import { computed, shallowRef } from "vue"
import { Codemirror } from "vue-codemirror"
import { useThemeStore } from "@/stores/theme"

/**
 * A CodeMirror editor for Graylog-only detection rules that treats the required
 * schema keys as LOCKED: their key token is highlighted, and any edit that would
 * delete or alter the `key:` itself is rejected (you can still edit the value).
 */
const code = defineModel<string>("code", { default: "" })

const emit = defineEmits<{ (e: "blocked", key: string): void }>()

const themeStore = useThemeStore()
const isDark = computed<boolean>(() => themeStore.isThemeDark)

// Required keys that must never be removed. `query` is the (indented) graylog query key.
const PROTECTED_KEYS = ["name", "id", "schema_version", "version", "description", "graylog", "query"]
const KEY_RE = new RegExp(`^(\\s*)(${PROTECTED_KEYS.join("|")})\\b\\s*:`)

interface KeySpan {
	lineFrom: number
	keyFrom: number
	keyTo: number // end of the key WORD (for the coloured mark)
	protTo: number // end of the protected span (through the colon)
	key: string
}

function computeSpans(doc: Text): KeySpan[] {
	const spans: KeySpan[] = []
	for (let i = 1; i <= doc.lines; i++) {
		const line = doc.line(i)
		const m = KEY_RE.exec(line.text)
		if (!m) continue
		const keyFrom = line.from + m[1].length
		const keyTo = keyFrom + m[2].length
		const colon = line.text.indexOf(":", m[1].length + m[2].length)
		spans.push({
			lineFrom: line.from,
			keyFrom,
			keyTo,
			protTo: line.from + (colon >= 0 ? colon + 1 : m[0].length),
			key: m[2]
		})
	}
	return spans
}

// --- decorations: tint the whole line + colour the key token ---------------
const lineDeco = Decoration.line({ class: "cm-required-line" })
const keyMark = Decoration.mark({ class: "cm-required-key" })

function buildDeco(doc: Text) {
	const ranges: ReturnType<typeof keyMark.range>[] = []
	for (const s of computeSpans(doc)) {
		ranges.push(lineDeco.range(s.lineFrom))
		ranges.push(keyMark.range(s.keyFrom, s.keyTo))
	}
	return Decoration.set(ranges, true)
}

const decoField = StateField.define({
	create: (state: EditorStateT) => buildDeco(state.doc),
	update: (value, tr) => (tr.docChanged ? buildDeco(tr.state.doc) : value),
	provide: f => EditorView.decorations.from(f)
})

// Marks transactions we dispatch ourselves (e.g. loading a template) so the
// required-field guard lets them through wholesale.
const programmatic = Annotation.define<boolean>()

// --- edit guard: prevent REMOVING a required key, but allow anything that
//     keeps them all (value edits, and full-document template replacement) -----
let lastBlockAt = 0
const guard = EditorState.transactionFilter.of(tr => {
	if (!tr.docChanged) return tr
	if (tr.annotation(programmatic)) return tr // our own template loads bypass the lock

	// Which protected key spans does this change touch (delete/alter the key token)?
	const before = computeSpans(tr.startState.doc)
	const touched = new Set<string>()
	tr.changes.iterChangedRanges((fromA, toA) => {
		for (const s of before) {
			// overlap of the change [fromA,toA] with the protected key span [keyFrom,protTo]
			if (fromA < s.protTo && toA > s.keyFrom) touched.add(s.key)
		}
	})
	if (touched.size === 0) return tr // no key token touched (e.g. value edit) → allow

	// A key token was touched. Allow it as long as EVERY required key still exists
	// afterwards — so a template reload (which contains them all) goes through, while
	// deleting or renaming a required key is rejected.
	const afterKeys = new Set(computeSpans(tr.newDoc).map(s => s.key))
	const missing = PROTECTED_KEYS.filter(k => !afterKeys.has(k))
	if (missing.length === 0) return tr

	const now = Date.now()
	if (now - lastBlockAt > 1200) {
		lastBlockAt = now
		emit("blocked", missing[0])
	}
	return [] // drop the transaction — the required key stays put
})

// --- jump-to-line: transient flash of a target line (used by the findings list) ---
const flashEffect = StateEffect.define<number | null>()
const flashLine = Decoration.line({ class: "cm-flash-line" })
const flashField = StateField.define<DecorationSet>({
	create: () => Decoration.none,
	update(value, tr) {
		value = value.map(tr.changes)
		for (const e of tr.effects) {
			if (e.is(flashEffect)) {
				if (e.value == null) {
					value = Decoration.none
				} else {
					const ln = Math.max(1, Math.min(e.value, tr.state.doc.lines))
					value = Decoration.set([flashLine.range(tr.state.doc.line(ln).from)])
				}
			}
		}
		return value
	},
	provide: f => EditorView.decorations.from(f)
})

const styling = EditorView.baseTheme({
	".cm-required-line": { backgroundColor: "rgba(2,132,199,0.07)", borderLeft: "2px solid #0284c7" },
	".cm-required-key": { color: "#0284c7", fontWeight: "600" },
	"&dark .cm-required-line": { backgroundColor: "rgba(56,189,248,0.10)", borderLeft: "2px solid #38bdf8" },
	"&dark .cm-required-key": { color: "#7dd3fc", fontWeight: "600" },
	".cm-flash-line": { animation: "cmFlash 1.3s ease-out" },
	"@keyframes cmFlash": {
		"0%": { backgroundColor: "rgba(245,158,11,0.45)" },
		"100%": { backgroundColor: "rgba(245,158,11,0)" }
	}
})

const extensions = computed<Extension[]>(() => {
	const list: Extension[] = [styling, decoField, flashField, guard, EditorView.lineWrapping]
	list.push(isDark.value ? oneDark : tomorrow)
	return list
})

const cmView = shallowRef<EditorView | null>(null)
function handleReady(payload: { view: EditorView }) {
	cmView.value = payload.view
}

/** Scroll a 1-based line into view, move the cursor there, and flash it. */
function goToLine(line: number) {
	const view = cmView.value
	if (!view || !line) return
	const ln = Math.max(1, Math.min(line, view.state.doc.lines))
	const pos = view.state.doc.line(ln).from
	view.dispatch({
		selection: { anchor: pos },
		effects: [EditorView.scrollIntoView(pos, { y: "center" }), flashEffect.of(ln)]
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

defineExpose({ goToLine, setContent })
</script>
