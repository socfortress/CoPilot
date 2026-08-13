<template>
	<n-tag :type="tagType" :size round :bordered="false">
		<template #icon>
			<Icon :name="icon" :size="14" />
		</template>
		{{ label }}
	</n-tag>
</template>

<script setup lang="ts">
import type { FileAnalysisVerdict } from "@/types/file-analysis"
import { NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = withDefaults(
	defineProps<{
		verdict?: FileAnalysisVerdict
		size?: "small" | "medium" | "large"
	}>(),
	{ verdict: "clean", size: "medium" }
)

const CleanIcon = "carbon:checkmark-outline"
const SuspiciousIcon = "carbon:warning-alt"
const MaliciousIcon = "carbon:warning-hex"

const tagType = computed<"success" | "warning" | "error">(() => {
	if (props.verdict === "malicious") return "error"
	if (props.verdict === "suspicious") return "warning"
	return "success"
})

const icon = computed(() => {
	if (props.verdict === "malicious") return MaliciousIcon
	if (props.verdict === "suspicious") return SuspiciousIcon
	return CleanIcon
})

const label = computed(() => (props.verdict || "clean").toUpperCase())
</script>
