<template>
	<div>{{ msg }}</div>
</template>
<script setup lang="ts">
// THIS COMPONENT IS USED FOR VITEST TESTING PURPOSES
import { toRefs } from "vue"
const props = defineProps(["msg"])
const { msg } = toRefs(props)
</script>
