<template>
	<YAMLEditor
		ref="yamlEditorRef"
		v-model:code="code"
		placeholder="Write a Graylog-only detection rule…"
		class="scrollbar-styled"
		:locked-keys="PROTECTED_KEYS"
		@blocked="emit('blocked', $event)"
	/>
</template>

<script setup lang="ts">
import type { YAMLEditorCtx } from "@/components/common/YAMLEditor.vue"
import { ref } from "vue"
import YAMLEditor from "@/components/common/YAMLEditor.vue"

const emit = defineEmits<{
	(e: "blocked", key: string): void
}>()

/**
 * The common YAML editor wired with the Graylog-only detection rule specifics:
 * the required schema keys are LOCKED, so their key token is highlighted and any
 * edit that would delete or rename the `key:` itself is rejected — the value stays
 * fully editable.
 */

// Required keys that must never be removed. `query` is the (indented) graylog query key.
const PROTECTED_KEYS = ["name", "id", "schema_version", "version", "description", "graylog", "query"]

const code = defineModel<string>("code", { default: "" })

const yamlEditorRef = ref<YAMLEditorCtx | null>(null)

/** Scroll a 1-based line into view, move the cursor there, and flash it. */
function goToLine(line: number) {
	yamlEditorRef.value?.goToLine(line)
}

/** Replace the whole document (used to load a fresh template) — always allowed. */
function setContent(text: string) {
	yamlEditorRef.value?.setContent(text)
}

defineExpose({ goToLine, setContent })
</script>
