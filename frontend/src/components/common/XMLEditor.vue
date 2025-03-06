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

import type { Extension } from "@codemirror/state"
import type { EditorView } from "@codemirror/view"
import { useThemeStore } from "@/stores/theme"
import { redo, redoDepth, undo, undoDepth } from "@codemirror/commands"
import { xml } from "@codemirror/lang-xml"
import { oneDark } from "@codemirror/theme-one-dark"
import { tomorrow } from "thememirror"
import { computed, onMounted, ref, shallowRef, watch } from "vue"
import { Codemirror } from "vue-codemirror"

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

const extensions = computed(() => {
	const list: Extension[] = [xml()]

	if (isDark.value) {
		list.push(oneDark)
	} else {
		list.push(tomorrow)
	}

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
