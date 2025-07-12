<template>
	<codemirror
		v-model="code"
		placeholder="Code goes here..."
		autofocus
		indent-with-tab
		:tab-size="4"
		:extensions
		style="height: 100%"
		@ready="handleReady"
	/>
</template>

<script setup lang="ts">
// EVALUATE: https://www.npmjs.com/package/vue3-ace-editor
// EVALUATE: https://github.surmon.me/vue-codemirror
// EVALUATE: https://www.npmjs.com/package/@guolao/vue-monaco-editor

import type { Diagnostic } from "@codemirror/lint"
import type { Extension } from "@codemirror/state"
import { redo, redoDepth, undo, undoDepth } from "@codemirror/commands"
import { xml } from "@codemirror/lang-xml"
import { linter } from "@codemirror/lint"
import { oneDark } from "@codemirror/theme-one-dark"
import { EditorView } from "@codemirror/view"
import { XMLValidator } from "fast-xml-parser"
import _isEqual from "lodash/isEqual"
import _trim from "lodash/trim"
import _uniqWith from "lodash/uniqWith"
import { tomorrow } from "thememirror"
import { computed, onMounted, ref, shallowRef, watch } from "vue"
import { Codemirror } from "vue-codemirror"
import * as xmllint from "xmllint-wasm"
import { useThemeStore } from "@/stores/theme"

export interface XMLEditorCtx {
	undo: () => void
	redo: () => void
	scrollToLine: (line: number) => void
	canUndo: () => boolean
	canRedo: () => boolean
}

export interface XMLError {
	line: number
	column: number
	message: string
	level: "error"
}

const emit = defineEmits<{
	(e: "mounted", value: XMLEditorCtx): void
	(e: "errors", value: XMLError[]): void
}>()

const code = defineModel<string>("code", { default: "" })

const themeStore = useThemeStore()
const isDark = computed<boolean>(() => themeStore.isThemeDark)

function convertXMLErrorsToDiagnostics(errors: XMLError[], text: string): Diagnostic[] {
	const diagnostics: Diagnostic[] = []
	const lines = text.split("\n")

	emit(
		"errors",
		errors
			.map(o => ({ ...o, message: _trim(o.message) }))
			.filter(o => o.message !== "^")
			.sort((a, b) => a.line - b.line)
	)

	errors.forEach(error => {
		// Calculate position in text
		let from = 0
		for (let i = 0; i < error.line - 1; i++) {
			from += lines[i].length + 1 // +1 for newline
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

async function strategyXMLLint(text: string): Promise<XMLError[]> {
	try {
		const result = await xmllint.validateXML({
			xml: text,
			// Optional: Initial memory capacity in Web Assembly memory pages (1 = 6.4KiB) - 256
			// is minimum and default here (16MiB).
			initialMemoryPages: 256,
			// Optional: Maximum memory capacity, in Web Assembly memory pages. If not
			// set, this will also default to 256 pages. Max is 65536 (4GiB).
			// Use this to raise the memory limit if your XML to validate are large enough to
			// cause out of memory errors.
			// The following example would set the max memory to 2GiB.
			maxMemoryPages: 2 * xmllint.memoryPages.GiB,
			normalization: "format"
		})

		if (result.valid) {
			return []
		}

		const errors: XMLError[] = result.errors.map(error => ({
			line: error.loc?.lineNumber || 1,
			column: 1,
			message: error.message,
			level: "error"
		}))

		return errors
	} catch (err) {
		console.error(err)
		return []
	}
}

async function strategyFastXMLParser(text: string): Promise<XMLError[]> {
	try {
		const errors: XMLError[] = []

		const validation = XMLValidator.validate(text)

		if (validation === true) {
			return []
		}

		if (typeof validation === "object" && validation.err) {
			const error = validation.err

			errors.push({
				line: error.line || 1,
				column: error.col || 1,
				message: error.msg,
				level: "error"
			})
		}

		return errors
	} catch {
		return []
	}
}

async function validateXML(text: string): Promise<Diagnostic[]> {
	let errors: XMLError[] = []

	try {
		errors = await strategyXMLLint(text)
	} catch (err) {
		console.error(err)

		try {
			errors = await strategyFastXMLParser(text)
		} catch (err) {
			console.error(err)
		}
	}

	return convertXMLErrorsToDiagnostics(_uniqWith(errors, _isEqual), text)
}

const extensions = computed(() => {
	const list: Extension[] = [xml()]

	if (isDark.value) {
		list.push(oneDark)
	} else {
		list.push(tomorrow)
	}

	list.push(
		linter(async view => {
			const text = view.state.doc.toString()

			if (!text.trim()) {
				return []
			}

			return await validateXML(text)
		})
	)

	return list
})

const cmView = shallowRef<EditorView | null>(null)
const canUndo = ref<boolean>(false)
const canRedo = ref<boolean>(false)

function updateHistoryState() {
	canUndo.value = cmView.value ? !!undoDepth(cmView.value.state) : false
	canRedo.value = cmView.value ? !!redoDepth(cmView.value.state) : false
}

function handleReady({ view }: { view: EditorView }) {
	cmView.value = view
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

function scrollToLine(line: number) {
	if (cmView.value) {
		const view = cmView.value
		const lineInfo = view.state.doc.line(line)
		view.dispatch({
			effects: EditorView.scrollIntoView(lineInfo.from, { y: "center" })
		})
	}
}

watch(code, () => {
	updateHistoryState()
})

onMounted(() => {
	emit("mounted", {
		undo: handleUndo,
		redo: handleRedo,
		scrollToLine,
		canRedo: () => canRedo.value,
		canUndo: () => canUndo.value
	})
})
</script>
