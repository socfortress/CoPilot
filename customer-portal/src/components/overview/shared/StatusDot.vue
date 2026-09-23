<template>
	<span class="size-1.5 shrink-0 rounded-xs" :class="bgClass(color)" aria-hidden="true" />
</template>

<script setup lang="ts">
import type { StatusColor } from "./status"
import { bgClass } from "./status"

defineProps<{
	color: StatusColor
}>()
</script>
