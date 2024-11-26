<template>
	<CardEntity>
		<template #headerExtra>{{ formatDate(log.timestamp) }}</template>
		<template #default>
			<div class="flex flex-col gap-2">
				<CardEntity
					:embedded="eventTypeLower !== 'error'"
					:status="eventTypeLower === 'error' ? 'error' : undefined"
				>
					<div class="flex flex-wrap gap-3 font-mono">
						<div :class="`status-cat-${statusCategory}`">
							<code>{{ log.status_code }}</code>
						</div>
						<div :class="`method-${methodLower}`">
							<strong>{{ log.method }}</strong>
						</div>
						<div class="text-sm">
							{{ log.route }}
						</div>
					</div>
				</CardEntity>
				<div class="flex flex-col gap-1 px-1">
					{{ log.message }}

					<p v-if="log.additional_info">
						{{ log.additional_info }}
					</p>
				</div>
			</div>
		</template>

		<template #mainExtra>
			<div class="flex flex-wrap items-center gap-3">
				<Badge type="splitted" :color="eventTypeLower === LogEventType.ERROR ? 'danger' : 'primary'">
					<template #iconLeft>
						<Icon :name="eventTypeLower === LogEventType.ERROR ? ErrorIcon : InfoIcon" :size="14"></Icon>
					</template>
					<template #label>Type</template>
					<template #value>
						{{ log.event_type }}
					</template>
				</Badge>
				<Badge v-if="log.user_id" type="splitted" color="primary">
					<template #iconLeft>
						<Icon :name="UserIcon" :size="14"></Icon>
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
	</CardEntity>
</template>

<script setup lang="ts">
import type { User } from "@/types/user.d"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { type Log, LogEventType } from "@/types/logs.d"
import dayjs from "@/utils/dayjs"
import { computed } from "vue"

const { log, users } = defineProps<{ log: Log; users?: User[] }>()

const InfoIcon = "carbon:information"
const UserIcon = "carbon:user"
const ErrorIcon = "majesticons:exclamation-line"

const dFormats = useSettingsStore().dateFormat

const statusCategory = computed(() => log.status_code.toString()[0]?.toLowerCase())
const methodLower = computed(() => log.method.toLowerCase())
const eventTypeLower = computed(() => log.event_type.toLowerCase())
const username = computed(() => {
	if (!users?.length) return ""

	const user = users.find(o => o.id.toString() === log.user_id?.toString())

	return user?.username || ""
})

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetime)
}
</script>

<style lang="scss" scoped>
.status {
	&-cat-2 {
		color: var(--success-color);
	}
	&-cat-3 {
		color: var(--success-color);
	}
	&-cat-4 {
		color: var(--warning-color);
	}
	&-cat-5 {
		color: var(--error-color);
	}
}

.method {
	&-get {
		color: var(--secondary1-color);
	}
	&-option {
		color: var(--secondary3-color);
	}
	&-put {
		color: var(--secondary2-color);
	}
	&-post {
		color: var(--primary-color);
	}
	&-delete {
		color: var(--secondary4-color);
	}
}
</style>
