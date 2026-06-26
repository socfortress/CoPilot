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
			<div v-for="stat in resultStats" :key="stat.key" :class="resultStatClasses(stat.kind, stat.count)">
				<div :class="resultNumClasses(stat.kind, stat.count)">{{ stat.count }}</div>
				<div class="text-tertiary mt-1 text-xs tracking-wide uppercase">{{ stat.label }}</div>
			</div>
		</div>

		<div
			class="divide-border bg-default border-default flex max-h-80 flex-col divide-y overflow-y-auto rounded-lg border"
		>
			<div
				v-for="r of result.results"
				:key="r.rule_id"
				class="hover:bg-primary/4 flex items-center justify-between gap-3 px-3 py-2"
			>
				<div class="flex min-w-0 flex-col">
					<div class="text-default truncate text-sm">{{ r.rule_name || r.rule_id }}</div>
					<div v-if="r.reason" class="text-tertiary truncate text-xs">{{ r.reason }}</div>
				</div>
				<span class="shrink-0 whitespace-nowrap">
					<Badge :color="statusBadgeColor(r.status)" size="small">
						<template #value>{{ r.status }}</template>
					</Badge>
				</span>
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
import type { BulkProvisionGraylogAlertResponse, BulkProvisionRuleStatus } from "@/types/copilot-searches"
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

type ResultStatKind = "provisioned" | "skipped" | "failed"

const resultStats = computed(() => {
	if (!result.value) return []

	return [
		{
			key: "provisioned",
			label: "Provisioned",
			count: result.value.provisioned_count,
			kind: "provisioned" as const
		},
		{ key: "skipped", label: "Skipped", count: result.value.skipped_count, kind: "skipped" as const },
		{ key: "failed", label: "Failed", count: result.value.failed_count, kind: "failed" as const }
	]
})

function resultStatClasses(kind: ResultStatKind, count: number) {
	const base = "rounded-lg border border-default bg-default p-2.5 text-center"

	if (count <= 0) return `${base} text-secondary`
	if (kind === "provisioned") return `${base} border-success/45 bg-success/6 text-default`
	if (kind === "failed") return `${base} border-error/45 bg-error/6 text-default`
	return `${base} text-default`
}

function resultNumClasses(kind: ResultStatKind, count: number) {
	const base = "text-xl leading-none font-bold"

	if (count <= 0) return base
	if (kind === "provisioned") return `${base} text-success`
	if (kind === "failed") return `${base} text-error`
	return base
}

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
