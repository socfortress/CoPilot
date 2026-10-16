<template>
	<div
		class="border-default flex flex-col gap-1 rounded-md border px-2 py-1.5 text-xs"
		data-testid="talon-v2-tool"
		:data-tool-call-id="item.toolCallId"
		:data-state="item.state"
	>
		<div class="flex flex-wrap items-center gap-2">
			<Icon :name="icon" :size="13" :class="iconClass" />
			<span class="font-mono font-semibold" data-testid="talon-v2-tool-name">{{ name }}</span>
			<span class="text-tertiary" data-testid="talon-v2-tool-status">{{ status }}</span>
		</div>

		<div v-if="item.errorText" class="text-error" data-testid="talon-v2-tool-error">{{ item.errorText }}</div>

		<details v-if="hasInput" class="text-secondary" data-testid="talon-v2-tool-input">
			<summary class="cursor-pointer select-none">Arguments</summary>
			<div v-if="keys" class="mt-1" data-testid="talon-v2-tool-keys">
				Too long to show. Keys: {{ keys.length ? keys.join(", ") : "none" }}
			</div>
			<pre v-else class="bg-secondary mt-1 max-h-60 overflow-auto rounded p-2 font-mono whitespace-pre-wrap">{{
				inputText
			}}</pre>
		</details>

		<TalonApprovalPlaceholder v-if="item.approval" :key="item.approval.id" :approval="item.approval" />
	</div>
</template>

<script setup lang="ts">
// One tool call of a turn: its name, then its arguments as JSON text in a collapsed block
// (`{truncated, keys}` by key name only), then how it ended with talon-analyst's fixed summary or
// text. Everything here is text: the name, the arguments and the error come from the model or
// from talon-analyst and are never rendered as HTML or Markdown.
import type { TalonV2ToolItem } from "@/types/talonV2"
import { computed } from "vue"
import { describeToolOutput, formatToolInput, truncatedKeys } from "@/api/talonV2Parser"
import Icon from "@/components/common/Icon.vue"
import TalonApprovalPlaceholder from "./TalonApprovalPlaceholder.vue"

const { item, live = false } = defineProps<{
	item: TalonV2ToolItem
	/** The turn is still streaming: a call without an answer is running, not left unanswered. */
	live?: boolean
}>()

const name = computed(() => item.name || "earlier call")
const hasInput = computed(() => item.input !== undefined)
const keys = computed(() => truncatedKeys(item.input))
const inputText = computed(() => formatToolInput(item.input))

const status = computed(() => {
	switch (item.state) {
		case "input-streaming":
			return live ? "preparing" : "not run"
		case "input-available":
			return live ? "running" : "no answer"
		case "output-available": {
			const words = describeToolOutput(item.output)
			return ["done", ...words].join(" · ")
		}
		case "output-error":
			return "failed"
		case "output-denied":
			return "denied, expired or withdrawn"
		case "approval-requested":
			return "awaiting approval"
		case "approval-responded":
			return "decided"
		default:
			return ""
	}
})

const icon = computed(() => {
	switch (item.state) {
		case "output-available":
			return "carbon:checkmark-outline"
		case "output-error":
			return "carbon:warning"
		case "output-denied":
			return "carbon:misuse-outline"
		case "approval-requested":
		case "approval-responded":
			return "carbon:user-certification"
		default:
			return live ? "carbon:in-progress" : "carbon:tools"
	}
})

const iconClass = computed(() => ({
	"text-success": item.state === "output-available",
	"text-error": item.state === "output-error",
	"text-warning": item.state === "output-denied" || item.state === "approval-requested"
}))
</script>
