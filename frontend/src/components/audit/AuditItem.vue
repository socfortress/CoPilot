<template>
	<CardEntity
		size="small"
		embedded
		main-box-class="gap-2"
		header-box-class="flex-nowrap! items-start text-default!"
		:status="isFailure ? 'error' : undefined"
	>
		<template #headerMain>
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-primary font-mono text-sm leading-snug font-semibold">{{ entry.action }}</span>
				<Badge v-if="entityLabel" type="splitted" bright size="small">
					<template #label>Entity</template>
					<template #value>{{ entityLabel }}</template>
				</Badge>
			</div>
		</template>

		<template #headerExtra>
			<Badge type="splitted" bright size="small">
				<template #label>
					<Icon :name="TimeIcon" :size="12" />
					Time
				</template>
				<template #value>{{ formattedTimestamp }}</template>
			</Badge>
		</template>

		<template #default>
			<div class="flex flex-col gap-2">
				<p v-if="entry.details" class="text-secondary text-sm leading-relaxed">
					{{ entry.details }}
				</p>

				<div v-if="showValueDiff" class="flex flex-col gap-1.5">
					<div
						v-if="entry.old_value"
						class="border-default bg-secondary flex flex-col gap-1 rounded-md border px-2.5 py-2"
					>
						<span class="text-secondary text-3xs tracking-wider uppercase">Before</span>
						<span
							v-shiki="{ fallbackLang: 'json', decode: true }"
							class="mt-0.5 block font-mono text-xs leading-relaxed wrap-break-word"
						>
							<pre> {{ entry.old_value }} </pre>
						</span>
					</div>
					<div
						v-if="entry.new_value"
						class="border-default bg-secondary flex flex-col gap-1 rounded-md border px-2.5 py-2"
					>
						<span class="text-secondary text-3xs tracking-wider uppercase">After</span>
						<span
							v-shiki="{ fallbackLang: 'json', decode: true }"
							class="mt-0.5 block font-mono text-xs leading-relaxed wrap-break-word"
						>
							<pre> {{ entry.new_value }} </pre>
						</span>
					</div>
				</div>
			</div>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge type="splitted" bright size="small" :color="isFailure ? 'danger' : 'success'">
					<template #label>
						<Icon :name="isFailure ? FailIcon : OkIcon" :size="12" />
						Result
					</template>
					<template #value>{{ entry.result }}</template>
				</Badge>
				<Badge v-if="actorLabel" type="splitted" bright size="small" color="primary">
					<template #label>
						<Icon :name="UserIcon" :size="12" />
						Actor
					</template>
					<template #value>{{ actorLabel }}</template>
				</Badge>
				<Badge v-if="entry.customer_code" type="splitted" bright size="small">
					<template #label>Customer</template>
					<template #value>{{ entry.customer_code }}</template>
				</Badge>
				<Badge v-if="entry.source_ip" type="splitted" bright size="small">
					<template #label>IP</template>
					<template #value>{{ entry.source_ip }}</template>
				</Badge>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { AuditLogEntry } from "@/types/audit"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import vShiki from "@/directives/v-shiki"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const { entry } = defineProps<{ entry: AuditLogEntry }>()

const UserIcon = "carbon:user"
const OkIcon = "carbon:checkmark-filled"
const FailIcon = "carbon:warning-filled"
const TimeIcon = "carbon:time"

const dFormats = useSettingsStore().dateFormat

const isFailure = computed(() => entry.result?.toLowerCase() === "failure")
const actorLabel = computed(() => entry.actor_username || (entry.actor_user_id ? `#${entry.actor_user_id}` : ""))
const entityLabel = computed(() => {
	if (!entry.entity_type) return ""
	return entry.entity_id ? `${entry.entity_type}: ${entry.entity_id}` : entry.entity_type
})
const showValueDiff = computed(() => Boolean(entry.old_value || entry.new_value))
const formattedTimestamp = computed(() => String(formatDate(entry.timestamp, dFormats.datetime, { tz: true })))
</script>
