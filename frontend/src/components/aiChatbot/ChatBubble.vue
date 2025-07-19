<template>
	<div class="flex flex-col">
		<div class="text-secondary text-xs">{{ formatDate(entity.datetime, dFormats.datetime) }}</div>
		<div>{{ entity.body }}</div>
	</div>
</template>

<script setup lang="ts">
import { formatDate } from "@/utils"
import { useSettingsStore } from "@/stores/settings"

export interface ChatBubble {
	id: string
	datetime: Date
	body: string
	thought?: string
	server: string
	sender: "user" | "server"
}

const { entity } = defineProps<{ entity: ChatBubble }>()

const dFormats = useSettingsStore().dateFormat
</script>
