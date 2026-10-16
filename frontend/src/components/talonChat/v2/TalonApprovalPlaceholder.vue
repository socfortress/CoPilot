<template>
	<div
		class="border-default bg-secondary inline-flex items-center gap-2 self-start rounded-md border px-2 py-1 text-xs"
		data-testid="talon-v2-approval"
		:data-approval-id="approval.id"
	>
		<Icon :name="pending ? 'carbon:time' : 'carbon:checkmark-outline'" :size="13" />
		<span data-testid="talon-v2-approval-status">{{ label }}</span>
	</div>
</template>

<script setup lang="ts">
// A placeholder for an action proposal's approval card (talon-analyst M5-10, the stream's
// `tool-approval-request` / the read-back's approval parts). It shows only whether the proposal
// still waits: what the action is, its target and approve / deny come from CoPilot's own record
// of it (M5-11b replaces this card), never from the stream or the model's text.
import type { TalonV2Approval } from "@/types/talonV2"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const { approval } = defineProps<{ approval: TalonV2Approval }>()

const pending = computed(() => approval.status === "pending")
const label = computed(() => (pending.value ? "Approval pending" : `Approval ${approval.status}`))
</script>
