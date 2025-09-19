<template>
	<Icon :name="getLevelIcon(level)" :size />
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { ScaComplianceLevel } from "@/types/sca.d"

const { level, size } = defineProps<{ level: ScaComplianceLevel; size?: number }>()

function getLevelIcon(level: string): string {
	const iconMap: Record<string, string> = {
		[ScaComplianceLevel.Excellent]: "carbon:checkmark-filled",
		[ScaComplianceLevel.Good]: "carbon:checkmark",
		[ScaComplianceLevel.Average]: "carbon:warning",
		[ScaComplianceLevel.Poor]: "carbon:warning-alt",
		[ScaComplianceLevel.Critical]: "carbon:warning-hex-filled"
	}
	return iconMap[level] || "carbon:help"
}
</script>
