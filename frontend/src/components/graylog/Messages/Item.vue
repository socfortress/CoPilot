<template>
	<CardEntity>
		<template #headerMain>{{ message.caller }}</template>
		<template #headerExtra>{{ formatDate(message.timestamp, dFormats.datetimesec) }}</template>
		<template #default>{{ message.content }}</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { Message } from "@/types/graylog/messages.d"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const { message } = defineProps<{ message: Message }>()

const dFormats = useSettingsStore().dateFormat
</script>
