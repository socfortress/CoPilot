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
import type { EditorView } from "@codemirror/view"
import { redo, redoDepth, undo, undoDepth } from "@codemirror/commands"
import { xml } from "@codemirror/lang-xml"
import { linter } from "@codemirror/lint"
import { oneDark } from "@codemirror/theme-one-dark"
import { XMLValidator } from "fast-xml-parser"
import { tomorrow } from "thememirror"
import { computed, onMounted, ref, shallowRef, watch } from "vue"
import { Codemirror } from "vue-codemirror"
import * as xmllint from "xmllint-wasm"
import { useThemeStore } from "@/stores/theme"

export interface XMLEditorCtx {
	undo: () => void
	redo: () => void
	canUndo: () => boolean
	canRedo: () => boolean
}

const emit = defineEmits<{
	(e: "mounted", value: XMLEditorCtx): void
}>()

const code = defineModel<string>("code", { default: "" })

const themeStore = useThemeStore()
const isDark = computed<boolean>(() => themeStore.isThemeDark)

interface XMLError {
	line: number
	column: number
	message: string
	level: "error"
}

function convertXMLErrorsToDiagnostics(errors: XMLError[], text: string): Diagnostic[] {
	const diagnostics: Diagnostic[] = []
	const lines = text.split("\n")

	errors.forEach(error => {
		// Calcola la posizione nel testo
		let from = 0
		for (let i = 0; i < error.line - 1; i++) {
			from += lines[i].length + 1 // +1 per il newline
		}
		from += error.column - 1

		// Trova la fine dell'errore (fine della riga o fine del messaggio)
		const lineText = lines[error.line - 1] || ""
		const to = from + Math.min(lineText.length - (error.column - 1), 50) // Limita a 50 caratteri

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

async function strategyFallback(text: string): Promise<XMLError[]> {
	try {
		const errors = regexXMLAnalyzer(text)

		return errors
	} catch (err) {
		console.error(err)
		return []
	}
}

function regexXMLAnalyzer(text: string): XMLError[] {
	const errors: XMLError[] = []
	const lines = text.split("\n")

	lines.forEach((line, lineIndex) => {
		const lineNumber = lineIndex + 1

		// Controllo per tag non chiusi
		if (line.includes("<") && !line.includes(">")) {
			errors.push({
				line: lineNumber,
				column: line.indexOf("<") + 1,
				message: "Tag non chiuso - manca il carattere '>'",
				level: "error"
			})
		}

		// Controllo per tag non aperti
		if (line.includes(">") && !line.includes("<")) {
			errors.push({
				line: lineNumber,
				column: line.indexOf(">") + 1,
				message: "Tag non aperto - manca il carattere '<'",
				level: "error"
			})
		}

		// Controllo per entità XML non valide
		const entityMatch = line.match(/&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)[a-zA-Z]+/g)
		if (entityMatch) {
			entityMatch.forEach(match => {
				const index = line.indexOf(match)
				errors.push({
					line: lineNumber,
					column: index + 1,
					message: `Entità XML non valida: "${match}"`,
					level: "error"
				})
			})
		}

		// Controllo per attributi non quotati
		/*
		const attrMatch = line.match(/\s+([a-z][\w:]*)\s*=\s*(?!["'])[^\s>]+/gi)
		if (attrMatch) {
			attrMatch.forEach(match => {
				const index = line.indexOf(match)
				errors.push({
					line: lineNumber,
					column: index + 1,
					message: "Attributo deve essere racchiuso tra virgolette",
					level: "error"
				})
			})
		}
			*/

		// Controllo per commenti non chiusi
		if (line.includes("<!--") && !line.includes("-->")) {
			errors.push({
				line: lineNumber,
				column: line.indexOf("<!--") + 1,
				message: "Commento XML non chiuso",
				level: "error"
			})
		}

		// Controllo per dichiarazioni XML non chiuse
		if (line.includes("<?") && !line.includes("?>")) {
			errors.push({
				line: lineNumber,
				column: line.indexOf("<?") + 1,
				message: "Dichiarazione XML non chiusa",
				level: "error"
			})
		}

		// Controllo per sezioni CDATA non chiuse
		if (line.includes("<![CDATA[") && !line.includes("]]>")) {
			errors.push({
				line: lineNumber,
				column: line.indexOf("<![CDATA[") + 1,
				message: "Sezione CDATA non chiusa",
				level: "error"
			})
		}
	})

	return errors
}

async function validateXML(text: string): Promise<Diagnostic[]> {
	let errors: XMLError[] = []

	if (!errors.length) {
		try {
			errors = await strategyXMLLint(text)
		} catch (err) {
			console.error(err)
		}
	}

	if (!errors.length) {
		try {
			errors = await strategyFastXMLParser(text)
		} catch (err) {
			console.error(err)
		}
	}

	if (!errors.length) {
		try {
			errors = await strategyFallback(text)
		} catch (err) {
			console.error(err)
		}
	}

	return convertXMLErrorsToDiagnostics(errors, text)
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

watch(code, () => {
	updateHistoryState()
})

onMounted(() => {
	emit("mounted", {
		undo: handleUndo,
		redo: handleRedo,
		canRedo: () => canRedo.value,
		canUndo: () => canUndo.value
	})
})
</script>
