<template>
	<n-spin :show="loading">
		<CardEntity
			v-if="resolvedEntry"
			size="small"
			:embedded
			main-box-class="gap-2"
			header-box-class="font-display! text-default!"
			:status="isFailure ? 'error' : undefined"
		>
			<template #header>
				<div class="flex flex-col gap-1.5">
					<div class="flex items-start justify-between gap-4">
						<div class="flex min-w-0 items-center gap-2">
							<span class="text-default truncate text-sm leading-snug font-semibold">
								{{ resolvedEntry.action }}
							</span>
						</div>
						<time
							:datetime="resolvedEntry.timestamp"
							class="text-secondary shrink-0 font-mono text-xs leading-snug tabular-nums"
							:title="formattedTimestamp"
						>
							{{ formattedTimestamp }}
						</time>
					</div>

					<dl v-if="hasEntity" class="flex min-w-0 items-baseline gap-2 text-xs">
						<dt class="text-secondary shrink-0 tracking-wider uppercase">Entity</dt>
						<dd class="text-default min-w-0 truncate font-mono">
							<span v-if="resolvedEntry.entity_type">{{ resolvedEntry.entity_type }}</span>
							<template v-if="resolvedEntry.entity_type && resolvedEntry.entity_id">
								<span class="text-secondary mx-1">·</span>
							</template>
							<span v-if="resolvedEntry.entity_id" class="text-primary font-medium">
								{{ resolvedEntry.entity_id }}
							</span>
						</dd>
					</dl>
				</div>
			</template>

			<template #default>
				<div class="flex flex-col gap-2">
					<div
						v-if="resolvedEntry.details"
						class="border-default bg-secondary flex flex-col gap-1 rounded-md border px-2.5 py-2"
					>
						<span class="text-secondary text-3xs tracking-wider uppercase">Details</span>
						<span class="mt-0.5 block font-mono text-xs leading-relaxed wrap-break-word">
							{{ resolvedEntry.details }}
						</span>
					</div>

					<div v-if="showValueDiff" class="flex flex-col gap-1.5">
						<div
							v-if="resolvedEntry.old_value"
							class="border-default bg-secondary flex flex-col gap-1 rounded-md border px-2.5 py-2"
						>
							<span class="text-secondary text-3xs tracking-wider uppercase">Before</span>
							<span
								v-shiki="{ fallbackLang: 'json', decode: true }"
								class="mt-0.5 block font-mono text-xs leading-relaxed wrap-break-word"
							>
								<pre> {{ resolvedEntry.old_value }} </pre>
							</span>
						</div>
						<div
							v-if="resolvedEntry.new_value"
							class="border-default bg-secondary flex flex-col gap-1 rounded-md border px-2.5 py-2"
						>
							<span class="text-secondary text-3xs tracking-wider uppercase">After</span>
							<span
								v-shiki="{ fallbackLang: 'json', decode: true }"
								class="mt-0.5 block font-mono text-xs leading-relaxed wrap-break-word"
							>
								<pre> {{ resolvedEntry.new_value }} </pre>
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
						<template #value>{{ resolvedEntry.result }}</template>
					</Badge>
					<Badge v-if="actorLabel" type="splitted" bright size="small" color="primary">
						<template #label>
							<Icon :name="UserIcon" :size="12" />
							Actor
						</template>
						<template #value>{{ actorLabel }}</template>
					</Badge>
					<Badge v-if="resolvedEntry.customer_code" type="splitted" bright size="small">
						<template #label>Customer</template>
						<template #value>{{ resolvedEntry.customer_code }}</template>
					</Badge>
					<Badge v-if="resolvedEntry.source_ip" type="splitted" bright size="small">
						<template #label>IP</template>
						<template #value>{{ resolvedEntry.source_ip }}</template>
					</Badge>
					<Badge type="splitted" bright size="small">
						<template #label>ID</template>
						<template #value>#{{ resolvedEntry.id }}</template>
					</Badge>
				</div>
			</template>

			<template v-if="$slots.footerExtra" #footerExtra>
				<slot name="footerExtra" />
			</template>
		</CardEntity>
	</n-spin>
</template>

<script setup lang="ts">
import type { AuditLogEntry } from "@/types/audit"
import { NSpin } from "naive-ui"
import { computed } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import vShiki from "@/directives/v-shiki"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = withDefaults(
	defineProps<{
		entry?: AuditLogEntry | null
		entryId?: number | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: AuditLogEntry): void
}>()

const dFormats = useSettingsStore().dateFormat

const UserIcon = "carbon:user"
const OkIcon = "carbon:checkmark-filled"
const FailIcon = "carbon:warning-filled"

const { loading, entity: resolvedEntry } = useEntityDetails<AuditLogEntry, number>({
	entity: () => props.entry,
	id: () => props.entryId,
	fetch: (id, signal) =>
		Api.audit.getAuditLog(id, signal).then(res => ({
			entity: res.data.success ? (res.data.audit_log ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Audit entry not found.",
	errorMessage: "Failed to load audit entry.",
	onLoaded: value => emit("loaded", value)
})

const isFailure = computed(() => resolvedEntry.value?.result?.toLowerCase() === "failure")
const actorLabel = computed(
	() =>
		resolvedEntry.value?.actor_username ||
		(resolvedEntry.value?.actor_user_id ? `#${resolvedEntry.value.actor_user_id}` : "")
)
const hasEntity = computed(() => Boolean(resolvedEntry.value?.entity_type || resolvedEntry.value?.entity_id))
const showValueDiff = computed(() => Boolean(resolvedEntry.value?.old_value || resolvedEntry.value?.new_value))
const formattedTimestamp = computed(() =>
	resolvedEntry.value ? String(formatDate(resolvedEntry.value.timestamp, dFormats.datetime, { tz: true })) : ""
)

defineExpose({ loading, resolvedEntry })
</script>
