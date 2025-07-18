<template>
	<div class="flex flex-col overflow-hidden">
		<div class="grow overflow-hidden">
			<n-scrollbar>
				<div class="p-4">chat...</div>
			</n-scrollbar>
		</div>
		<div class="flex flex-col p-4">
			<ChatQuery />
		</div>
	</div>
</template>

<script setup lang="ts">
import { NScrollbar } from "naive-ui"
import ChatQuery from "./ChatQuery.vue"
</script>
