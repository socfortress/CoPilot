<template>
	<span
		class="inline-flex items-center gap-1 text-xs font-medium whitespace-nowrap"
		:style="{ color }"
		:data-state="state"
	>
		<Icon :name="meta.icon" :size="13" />
		{{ label ?? meta.label }}
	</span>
</template>

<script setup lang="ts">
// An SLA state as icon + word: status colour never travels alone.
import type { SlaState } from "@/types/soc-management"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SLA_STATE_META, TONE_COLOR } from "../utils"

const { state, label } = defineProps<{ state: SlaState; label?: string }>()

const meta = computed(() => SLA_STATE_META[state])
const color = computed(() =>
	meta.value.tone === "neutral" ? "var(--fg-secondary-color)" : TONE_COLOR[meta.value.tone]
)
</script>
