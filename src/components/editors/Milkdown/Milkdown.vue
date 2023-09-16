<template>
	<MilkdownProvider>
		<Editor />
	</MilkdownProvider>
</template>

<script setup lang="ts">
import { MilkdownProvider } from "@milkdown/vue"
import Editor from "./Editor.vue"
</script>
