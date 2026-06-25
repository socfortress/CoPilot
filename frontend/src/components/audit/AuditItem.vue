<template>
	<CardEntity>
		<template #headerExtra>{{ formatDate(entry.timestamp) }}</template>
		<template #default>
			<div class="flex flex-col gap-2">
				<div class="flex flex-wrap items-center gap-3 font-mono">
					<code class="action">{{ entry.action }}</code>
					<div v-if="entry.entity_type" class="text-sm">
						{{ entry.entity_type }}
						<strong v-if="entry.entity_id">: {{ entry.entity_id }}</strong>
					</div>
				</div>

				<div v-if="entry.details" class="px-1 text-sm">
					{{ entry.details }}
				</div>

				<div v-if="entry.old_value || entry.new_value" class="flex flex-col gap-1 px-1 text-xs">
					<div v-if="entry.old_value" class="flex flex-wrap gap-2">
						<span class="text-secondary">Before:</span>
						<code class="wrap-break-word">{{ stringify(entry.old_value) }}</code>
					</div>
					<div v-if="entry.new_value" class="flex flex-wrap gap-2">
						<span class="text-secondary">After:</span>
						<code class="wrap-break-word">{{ stringify(entry.new_value) }}</code>
					</div>
				</div>
			</div>
		</template>

		<template #mainExtra>
			<div class="flex flex-wrap items-center gap-3">
				<Badge type="splitted" :color="isFailure ? 'danger' : 'success'">
					<template #iconLeft>
						<Icon :name="isFailure ? FailIcon : OkIcon" :size="14" />
					</template>
					<template #label>Result</template>
					<template #value>{{ entry.result }}</template>
				</Badge>
				<Badge v-if="actorLabel" type="splitted" color="primary">
					<template #iconLeft>
						<Icon :name="UserIcon" :size="14" />
					</template>
					<template #label>Actor</template>
					<template #value>{{ actorLabel }}</template>
				</Badge>
				<Badge v-if="entry.customer_code" type="muted">
					<template #label>Customer</template>
					<template #value>{{ entry.customer_code }}</template>
				</Badge>
				<Badge v-if="entry.source_ip" type="muted">
					<template #label>IP</template>
					<template #value>{{ entry.source_ip }}</template>
				</Badge>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { AuditLogEntry } from "@/types/audit.d"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const { entry } = defineProps<{ entry: AuditLogEntry }>()

const UserIcon = "carbon:user"
const OkIcon = "carbon:checkmark-outline"
const FailIcon = "majesticons:exclamation-line"

const dFormats = useSettingsStore().dateFormat

const isFailure = computed(() => entry.result?.toLowerCase() === "failure")
const actorLabel = computed(() => entry.actor_username || (entry.actor_user_id ? `#${entry.actor_user_id}` : ""))

function stringify(value: Record<string, unknown> | null): string {
	if (!value) return ""
	try {
		return JSON.stringify(value)
	} catch {
		return String(value)
	}
}

function formatDate(timestamp: string | number | Date): string {
	// Backend stores UTC without a 'Z' suffix; parse as UTC then convert to local.
	return dayjs.utc(timestamp).local().format(dFormats.datetime)
}
</script>

<style lang="scss" scoped>
.action {
	color: var(--primary-color);
	font-weight: bold;
}
</style>
