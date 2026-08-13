<template>
	<CardEntity>
		<template #headerMain>
			<div class="text-default flex flex-wrap items-center gap-3">
				<Badge type="splitted" :color="eventTypeLower === LogEventType.ERROR ? 'danger' : 'primary'">
					<template #iconLeft>
						<Icon :name="eventTypeLower === LogEventType.ERROR ? ErrorIcon : InfoIcon" :size="14" />
					</template>
					<template #label>Type</template>
					<template #value>
						{{ log.event_type }}
					</template>
				</Badge>
				<Badge v-if="log.user_id" type="splitted" color="primary">
					<template #iconLeft>
						<Icon :name="UserIcon" :size="14" />
					</template>
					<template #value>
						<span class="flex items-center gap-2">
							<span>#{{ log.user_id }}</span>
							<span v-if="username" class="flex gap-2">
								<span>/</span>
								<span>
									{{ username }}
								</span>
							</span>
						</span>
					</template>
				</Badge>
			</div>
		</template>
		<template #headerExtra>{{ formatDate(log.timestamp) }}</template>
		<template #default>
			<div class="flex flex-col gap-2">
				<CardEntity
					:embedded="eventTypeLower !== 'error'"
					:status="eventTypeLower === 'error' ? 'error' : undefined"
				>
					<div class="flex flex-wrap gap-3 font-mono">
						<div :class="statusColorClass">
							<code>{{ log.status_code }}</code>
						</div>
						<div :class="methodColorClass">
							<strong>{{ log.method ?? "—" }}</strong>
						</div>
						<div class="text-sm">
							{{ log.route ?? "—" }}
						</div>
					</div>
				</CardEntity>
				<n-card embedded size="small">
					<div class="flex flex-col gap-1">
						{{ log.message }}

						<p v-if="log.additional_info">
							{{ log.additional_info }}
						</p>
					</div>
				</n-card>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { Log } from "@/types/logs"
import type { User } from "@/types/user"
import { NCard } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { LogEventType } from "@/types/logs"
import dayjs from "@/utils/dayjs"

const { log, users } = defineProps<{ log: Log; users?: User[] }>()

const InfoIcon = "carbon:information"
const UserIcon = "carbon:user"
const ErrorIcon = "majesticons:exclamation-line"

const dFormats = useSettingsStore().dateFormat

const statusCategory = computed(() => log.status_code.toString()[0]?.toLowerCase())
const methodLower = computed(() => log.method?.toLowerCase() ?? "")
const eventTypeLower = computed(() => log.event_type.toLowerCase())
const username = computed(() => {
	if (!users?.length) return ""

	const user = users.find(o => o.id.toString() === log.user_id?.toString())

	return user?.username || ""
})

const statusColorClass = computed(() => {
	if (statusCategory.value === "2" || statusCategory.value === "3") {
		return "text-success"
	}
	if (statusCategory.value === "4") {
		return "text-warning"
	}
	if (statusCategory.value === "5") {
		return "text-error"
	}
	return ""
})

const methodColorClass = computed(() => {
	switch (methodLower.value) {
		case "get":
			return "text-extra-1"
		case "option":
			return "text-extra-3"
		case "put":
			return "text-extra-2"
		case "post":
			return "text-primary"
		case "delete":
			return "text-error"
		default:
			return ""
	}
})

function formatDate(timestamp: string | number | Date): string {
	// Parse as UTC (since backend stores in UTC without 'Z' suffix - maybe address later), then convert to local
	return dayjs.utc(timestamp).local().format(dFormats.datetime)
}
</script>
