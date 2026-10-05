<template>
	<span
		v-if="delta"
		class="delta-chip text-2xs inline-flex items-center gap-0.5 rounded-full px-1.5 py-px font-mono leading-4"
		:style="{ color, backgroundColor: wash }"
		:title="`${delta.label} vs previous period`"
		data-testid="delta-chip"
	>
		<Icon :name="icon" :size="11" />
		{{ delta.label }}
	</span>
</template>

<script setup lang="ts">
import type { Delta } from "../utils"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { TONE_COLOR } from "../utils"

const { delta } = defineProps<{ delta: Delta | null }>()

const ICONS = { up: "carbon:arrow-up-right", down: "carbon:arrow-down-right", flat: "carbon:arrow-right" } as const

const icon = computed(() => ICONS[delta?.direction ?? "flat"])
const color = computed(() => TONE_COLOR[delta?.tone ?? "neutral"])
const wash = computed(() => `color-mix(in srgb, ${color.value} 12%, transparent)`)
</script>
