<template>
	<Badge :color="getComplianceLevelColor(getComplianceLevel(score))" type="splitted" bright class="whitespace-nowrap">
		<template #iconLeft>
			<ScaLevelIcon :level="getComplianceLevel(score)" :size="14" />
		</template>
		<template #label>Score</template>
		<template #value>{{ score }}%</template>
	</Badge>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import Badge from "@/components/common/Badge.vue"
import { ScaComplianceLevel } from "@/types/sca.d"
import ScaLevelIcon from "./ScaLevelIcon.vue"
import { getComplianceLevel } from "./utils"

const { score } = defineProps<{ score: number }>()

function getComplianceLevelColor(level: ScaComplianceLevel): BadgeColor {
	switch (level) {
		case ScaComplianceLevel.Excellent:
			return "success"
		case ScaComplianceLevel.Good:
			return "primary"
		case ScaComplianceLevel.Average:
			return "warning"
		case ScaComplianceLevel.Poor:
			return "warning"
		case ScaComplianceLevel.Critical:
			return "danger"
		default:
			return "primary"
	}
}
</script>
