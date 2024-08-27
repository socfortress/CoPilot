<template>
	<Icon :name="assignee ? AssigneeIcon : WarningIcon" :size="size || 16" />
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ assignee: string | null; size?: number }>()
const { assignee, size } = toRefs(props)

const AssigneeIcon = "carbon:user-military"
const WarningIcon = "carbon:warning-hex"
</script>
