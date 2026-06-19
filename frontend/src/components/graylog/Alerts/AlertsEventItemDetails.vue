<template>
	<div class="grid-auto-fit-200 grid gap-2 p-6">
		<CardKV>
			<template #key>event_definition_id</template>
			<template #value>
				<button
					type="button"
					class="text-primary flex items-center gap-1 font-mono"
					@click="emit('clickEvent', alertsEvent.event.event_definition_id)"
				>
					{{ alertsEvent.event.event_definition_id }}
					<Icon :name="LinkIcon" :size="13" />
				</button>
			</template>
		</CardKV>

		<CardKV>
			<template #key>event_definition_type</template>
			<template #value>
				<span class="font-mono">{{ alertsEvent.event.event_definition_type }}</span>
			</template>
		</CardKV>

		<CardKV>
			<template #key>source</template>
			<template #value>
				<span class="font-mono">{{ alertsEvent.event.source }}</span>
			</template>
		</CardKV>

		<CardKV>
			<template #key>index_name</template>
			<template #value>
				<button
					type="button"
					class="text-primary flex items-center gap-1 font-mono"
					@click="routeIndex(alertsEvent.index_name).navigate()"
				>
					{{ alertsEvent.index_name }}
					<Icon :name="LinkIcon" :size="13" />
				</button>
			</template>
		</CardKV>

		<CardKV>
			<template #key>index_type</template>
			<template #value>
				<span class="font-mono">{{ alertsEvent.index_type }}</span>
			</template>
		</CardKV>

		<CardKV>
			<template #key>timestamp</template>
			<template #value>
				<span class="font-mono">{{ formatDateTime(alertsEvent.event.timestamp) }}</span>
			</template>
		</CardKV>

		<CardKV>
			<template #key>timestamp processing</template>
			<template #value>
				<span class="font-mono">{{ formatDateTime(alertsEvent.event.timestamp_processing) }}</span>
			</template>
		</CardKV>
	</div>
</template>

<script setup lang="ts">
import type { AlertsEventElement } from "@/types/graylog/alerts.d"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const { alertsEvent } = defineProps<{ alertsEvent: AlertsEventElement }>()

const emit = defineEmits<{
	(e: "clickEvent", value: string): void
}>()

const LinkIcon = "carbon:launch"

const dFormats = useSettingsStore().dateFormat
const { routeIndex } = useNavigation()

function formatDateTime(timestamp: string): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}
</script>
