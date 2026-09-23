<template>
	<!-- Status never rides on colour alone: every pill carries an icon and a word. -->
	<n-tag :type="look.type" size="small" round :bordered="false" class="min-w-24 justify-center">
		<template #icon><Icon :name="look.icon" :size="12" /></template>
		{{ look.label }}
	</n-tag>
</template>

<script setup lang="ts">
import { NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const { action } = defineProps<{ action: string }>()

const LOOKS: Record<string, { type: "error" | "warning" | "default"; icon: string; label: string }> = {
	blocked: { type: "error", icon: "carbon:locked", label: "blocked" },
	detected: { type: "warning", icon: "carbon:warning-alt", label: "detected" },
	passed: { type: "default", icon: "carbon:checkmark", label: "passed" }
}

const look = computed(() => LOOKS[action] ?? { type: "default" as const, icon: "carbon:information", label: action })
</script>
