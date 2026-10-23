<template>
	<span
		class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap"
		:style="{ color, borderColor: color }"
		:data-status="normalized"
		data-testid="talon-health-status"
	>
		<Icon :name="meta.icon" :size="13" />
		{{ label ?? meta.label }}
	</span>
</template>

<script setup lang="ts">
// A component's status as icon + word in its status colour: the colour never travels alone.
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { TONE_COLOR } from "@/components/socManagement/utils"
import { componentStatus, STATUS_META } from "./health"

const { status, label } = defineProps<{ status: unknown; label?: string }>()

const normalized = computed(() => componentStatus(status))
const meta = computed(() => STATUS_META[normalized.value])
const color = computed(() => TONE_COLOR[meta.value.tone])
</script>
