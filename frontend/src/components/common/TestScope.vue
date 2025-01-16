<template>
	<div>{{ msg }}</div>
</template>

<script setup lang="ts">
// THIS COMPONENT IS USED FOR VITEST TESTING PURPOSES
const { msg } = defineProps<{ msg: string }>()
</script>
