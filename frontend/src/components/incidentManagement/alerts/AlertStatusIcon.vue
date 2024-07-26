<template>
	<Icon
		:name="status === 'OPEN' ? WarningIcon : status === 'IN_PROGRESS' ? ProgressIcon : CheckIcon"
		:size="size || 16"
	/>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"
import type { AlertStatus } from "@/types/incidentManagement/alerts.d"

const props = defineProps<{ status: AlertStatus; size?: number }>()
const { status, size } = toRefs(props)

const ProgressIcon = "carbon:hourglass"
const CheckIcon = "carbon:checkmark-outline"
const WarningIcon = "carbon:warning-hex"
</script>
