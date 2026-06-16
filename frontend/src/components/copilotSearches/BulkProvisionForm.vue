<template>
	<div v-if="!result" class="flex flex-col gap-3">
		<n-alert type="info" :show-icon="false">
			This will create one Graylog event definition per rule, using the shared configuration below. Rules whose
			alert title already exists in Graylog are skipped automatically. Rules without a Graylog query are also
			skipped.
		</n-alert>

		<div class="grid grid-cols-2 gap-3">
			<div class="flex flex-col gap-1">
				<label class="text-secondary text-xs">Search within (seconds)</label>
				<n-input-number v-model:value="config.search_within_seconds" :min="60" :max="86400" size="small" />
			</div>
			<div class="flex flex-col gap-1">
				<label class="text-secondary text-xs">Execute every (seconds)</label>
				<n-input-number v-model:value="config.execute_every_seconds" :min="60" :max="86400" size="small" />
			</div>
			<div class="flex flex-col gap-1">
				<label class="text-secondary text-xs">Priority</label>
				<n-select v-model:value="config.priority" :options="priorityOptions" size="small" />
			</div>
			<div class="flex flex-col gap-1">
				<label class="text-secondary text-xs">Event limit</label>
				<n-input-number v-model:value="config.event_limit" :min="1" :max="10000" size="small" />
			</div>
		</div>

		<div class="text-secondary text-xs">
			About to provision
			<strong>{{ provisionableCount }}</strong>
			rule{{ provisionableCount === 1 ? "" : "s" }}.
		</div>

		<div class="flex justify-end gap-2">
			<n-button size="small" quaternary :disabled="submitting" @click="emit('close')">Cancel</n-button>
			<n-button size="small" type="primary" :loading="submitting" :disabled="!provisionableCount" @click="submit">
				Provision {{ provisionableCount }} rule{{ provisionableCount === 1 ? "" : "s" }}
			</n-button>
		</div>
	</div>

	<div v-else class="flex flex-col gap-3">
		<div class="grid grid-cols-3 gap-2">
			<div class="result-stat" :class="{ 'is-active result-provisioned': result.provisioned_count > 0 }">
				<div class="result-num">{{ result.provisioned_count }}</div>
				<div class="result-label">Provisioned</div>
			</div>
			<div class="result-stat" :class="{ 'is-active': result.skipped_count > 0 }">
				<div class="result-num">{{ result.skipped_count }}</div>
				<div class="result-label">Skipped</div>
			</div>
			<div class="result-stat" :class="{ 'is-active result-failed': result.failed_count > 0 }">
				<div class="result-num">{{ result.failed_count }}</div>
				<div class="result-label">Failed</div>
			</div>
		</div>

		<div class="bulk-results-list">
			<div v-for="r of result.results" :key="r.rule_id" class="bulk-result-row">
				<div class="flex min-w-0 flex-col">
					<div class="text-default truncate text-sm">{{ r.rule_name || r.rule_id }}</div>
					<div v-if="r.reason" class="text-tertiary truncate text-xs">{{ r.reason }}</div>
				</div>
				<Badge :color="statusBadgeColor(r.status)" size="small">
					<template #value>{{ r.status }}</template>
				</Badge>
			</div>
		</div>

		<div class="flex justify-end">
			<n-button size="small" type="primary" @click="close">Done</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { ApiError } from "@/types/common"
import type { BulkProvisionGraylogAlertResponse, BulkProvisionRuleStatus } from "@/types/copilotSearches.d"
import { NAlert, NButton, NInputNumber, NSelect, useMessage } from "naive-ui"
import { computed, reactive, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	/** Rule IDs to provision. Caller should pass only IDs that have a Graylog query if known. */
	ruleIds: string[]
	/** Optional override for the displayed count. Defaults to ruleIds.length. */
	provisionableCount?: number
}>()

const emit = defineEmits<{
	(e: "close"): void
	(e: "success", result: BulkProvisionGraylogAlertResponse): void
}>()

const message = useMessage()

const submitting = ref(false)
const result = ref<BulkProvisionGraylogAlertResponse | null>(null)

const config = reactive({
	search_within_seconds: 300,
	execute_every_seconds: 300,
	priority: 2 as 1 | 2 | 3,
	event_limit: 1000
})

const priorityOptions = [
	{ label: "Low", value: 1 },
	{ label: "Normal", value: 2 },
	{ label: "High", value: 3 }
]

const provisionableCount = computed(() => props.provisionableCount ?? props.ruleIds.length)

async function submit() {
	if (!props.ruleIds.length) return
	submitting.value = true
	try {
		const res = await Api.copilotSearches.bulkProvisionGraylogAlerts({
			rule_ids: props.ruleIds,
			search_within_seconds: config.search_within_seconds,
			execute_every_seconds: config.execute_every_seconds,
			priority: config.priority,
			event_limit: config.event_limit
		})
		result.value = res.data
		emit("success", res.data)
		if (res.data.failed_count === 0) message.success(res.data.message)
		else message.warning(res.data.message)
	} catch (err) {
		const error = err as { response?: { data?: { message?: string } } }
		message.error(getApiErrorMessage(error as ApiError) || "Bulk provision failed")
	} finally {
		submitting.value = false
	}
}

function close() {
	emit("close")
	setTimeout(() => {
		result.value = null
	}, 250)
}

watch(
	() => props.ruleIds,
	() => {
		result.value = null
	},
	{ deep: true }
)

function statusBadgeColor(status: BulkProvisionRuleStatus): BadgeColor | undefined {
	switch (status) {
		case "provisioned":
			return "success"
		case "failed":
			return "danger"
		case "skipped":
			return undefined
	}
}
</script>

<style scoped lang="scss">
.result-stat {
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background: var(--bg-default-color);
	padding: 10px;
	text-align: center;
	color: var(--fg-secondary-color);
}
.result-stat.is-active {
	color: var(--fg-default-color);
}
.result-stat.result-provisioned.is-active {
	border-color: rgba(var(--success-color-rgb) / 0.45);
	background: rgba(var(--success-color-rgb) / 0.06);
}
.result-stat.result-failed.is-active {
	border-color: rgba(var(--error-color-rgb) / 0.45);
	background: rgba(var(--error-color-rgb) / 0.06);
}
.result-num {
	font-size: 1.4rem;
	font-weight: 700;
	line-height: 1;
}
.result-stat.is-active .result-num {
	color: inherit;
}
.result-stat.result-provisioned.is-active .result-num {
	color: var(--success-color);
}
.result-stat.result-failed.is-active .result-num {
	color: var(--error-color);
}
.result-label {
	font-size: 0.7rem;
	color: var(--fg-tertiary-color);
	text-transform: uppercase;
	letter-spacing: 0.04em;
	margin-top: 4px;
}

.bulk-results-list {
	max-height: 320px;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background: var(--bg-default-color);
}

.bulk-result-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	padding: 8px 12px;
}
.bulk-result-row + .bulk-result-row {
	border-top: 1px solid var(--border-color);
}
.bulk-result-row:hover {
	background: rgba(var(--primary-color-rgb) / 0.04);
}

.bulk-result-row :deep(.badge) {
	flex-shrink: 0;
	white-space: nowrap;
}
</style>
