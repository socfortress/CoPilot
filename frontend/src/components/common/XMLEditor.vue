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
import { redo, undo } from "@codemirror/commands"
import { xml } from "@codemirror/lang-xml"
import { oneDark } from "@codemirror/theme-one-dark"
import { tomorrow } from "thememirror"
import { computed, onMounted, shallowRef } from "vue"
import { Codemirror } from "vue-codemirror"

export interface XMLEditorCtx {
	undo: () => void
	redo: () => void
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

const cmView = shallowRef<EditorView>()
function handleReady({ view }: any) {
	cmView.value = view
}

function handleUndo() {
	undo({
		state: cmView.value!.state,
		dispatch: cmView.value!.dispatch
	})
}

function handleRedo() {
	redo({
		state: cmView.value!.state,
		dispatch: cmView.value!.dispatch
	})
}

onMounted(() => {
	emit("mounted", {
		undo: handleUndo,
		redo: handleRedo
	})
})
</script>
