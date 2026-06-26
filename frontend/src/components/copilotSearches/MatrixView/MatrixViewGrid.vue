<template>
	<div ref="matrixScrollWrapRef" class="relative" :style="matrixScrollWrapStyle">
		<n-spin v-if="loading && coverage" show class="absolute inset-0 flex items-center justify-center" />

		<div
			class="scrollbar-styled bg-secondary border-default h-full overflow-auto rounded-lg border pb-1"
			:class="{ 'opacity-55': loading && coverage }"
		>
			<n-empty
				v-if="!loading && coverage && filteredTactics.length === 0"
				description="No techniques match your filters."
				class="min-h-96"
			>
				<template #extra>
					<n-button size="small" @click="emit('clear-filters')">Clear filters</n-button>
				</template>
			</n-empty>

			<n-spin v-else-if="loading && !coverage" show class="flex min-h-96 w-full items-center justify-center" />

			<div v-else class="flex min-w-max gap-1.5 p-1">
				<TacticsColumn
					v-for="tactic of filteredTactics"
					:key="tactic.id"
					v-model:expanded="expanded"
					:tactic
					:coverage
					:rules-index
					:hovered-technique-id
					:hovered-tactic-id
					v-on="gridListeners"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type {
	MitreCoverageResponse,
	MitreRuleIndexEntry,
	MitreSubTechnique,
	MitreTactic,
	MitreTechnique
} from "@/types/copilot-searches"
import { useElementBounding, useWindowSize } from "@vueuse/core"
import { NButton, NEmpty, NSpin } from "naive-ui"
import { computed, ref, useTemplateRef } from "vue"
import TacticsColumn from "./TacticsColumn.vue"

defineProps<{
	loading: boolean
	coverage: MitreCoverageResponse | null
	filteredTactics: MitreTactic[]
	rulesIndex: Record<string, MitreRuleIndexEntry>
}>()

const emit = defineEmits<{
	(e: "clear-filters"): void
	(e: "open-technique", tactic: MitreTactic, tech: MitreTechnique): void
	(e: "open-sub-technique", tactic: MitreTactic, tech: MitreTechnique, sub: MitreSubTechnique): void
	(e: "open-rule", ruleId: string): void
}>()

const expanded = defineModel<Record<string, boolean>>("expanded", { required: true })

const matrixScrollWrapRef = useTemplateRef<HTMLDivElement>("matrixScrollWrapRef")
const { top: matrixScrollWrapTop } = useElementBounding(matrixScrollWrapRef)
const { height: viewportHeight } = useWindowSize()

const matrixScrollWrapStyle = computed(() => {
	const height = viewportHeight.value - matrixScrollWrapTop.value - 50
	if (height <= 0) return undefined
	return { height: `${Math.floor(height)}px` }
})

const hoveredTechniqueId = ref<string | null>(null)
const hoveredTacticId = ref<string | null>(null)

const gridListeners = {
	"open-technique": (t: MitreTactic, tech: MitreTechnique) => emit("open-technique", t, tech),
	"open-sub-technique": (t: MitreTactic, tech: MitreTechnique, sub: MitreSubTechnique) =>
		emit("open-sub-technique", t, tech, sub),
	"open-rule": (ruleId: string) => emit("open-rule", ruleId),
	"technique-hover": (tacticId: string, techId: string) => {
		hoveredTacticId.value = tacticId
		hoveredTechniqueId.value = techId
	},
	"technique-leave": () => {
		hoveredTacticId.value = null
		hoveredTechniqueId.value = null
	}
}
</script>
