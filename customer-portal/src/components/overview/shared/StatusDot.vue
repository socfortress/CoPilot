<template>
	<span class="status-dot" :style="{ backgroundColor: colorVar(color) }" aria-hidden="true" />
</template>

<script setup lang="ts">
import type { StatusColor } from "./status"
import { colorVar } from "./status"

defineProps<{
	color: StatusColor
}>()
</script>

<style lang="scss" scoped>
.status-dot {
	width: 6px;
	height: 6px;
	border-radius: 2px;
	flex-shrink: 0;
}
</style>
