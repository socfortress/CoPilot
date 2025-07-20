<template>
	<div
		class="flex flex-col gap-0.5"
		:class="{
			'items-end text-right': entity.sender === 'user'
		}"
	>
		<div class="text-secondary text-sm font-semibold" v-if="entity.sender === 'server'">{{ entity.server }}:</div>
		<div
			class="[&_*:last-child]:mb-2! [&_*]:text-sm"
			:class="{
				'bg-secondary max-w-11/12 rounded-lg px-2 py-1 text-sm': entity.sender === 'user'
			}"
		>
			<template v-if="entity.sender === 'user'">
				{{ entity.body }}
			</template>
			<Suspense v-else>
				<Markdown :source="entity.body" />
			</Suspense>
		</div>
		<div class="text-tertiary text-xs">
			{{ formatDate(entity.datetime, dFormats.datetime) }}
		</div>
	</div>
</template>

<script setup lang="ts">
import { formatDate } from "@/utils"
import { useSettingsStore } from "@/stores/settings"
import { defineAsyncComponent } from "vue"

export interface ChatBubble {
	id: string
	datetime: Date
	body: string
	thought?: string
	server: string
	sender: "user" | "server"
}

const { entity } = defineProps<{ entity: ChatBubble }>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const dFormats = useSettingsStore().dateFormat
</script>
