<template>
	<div v-if="technique" class="flex flex-col gap-3">
		<n-timeline>
			<n-timeline-item v-if="technique.url">
				<a :href="technique.url" target="_blank" rel="noopener">
					{{ technique.id }} — view on attack.mitre.org ↗
				</a>
			</n-timeline-item>
			<n-timeline-item v-if="subTechnique" type="info">
				<div class="text-secondary text-sm">
					Sub-technique:
					<a v-if="subTechnique.url" :href="subTechnique.url" target="_blank" rel="noopener">
						{{ subTechnique.id }} {{ subTechnique.name }} ↗
					</a>
					<span v-else>{{ subTechnique.id }} {{ subTechnique.name }}</span>
				</div>
			</n-timeline-item>
		</n-timeline>

		<div
			v-if="provisionableCount > 0"
			class="border-default bg-secondary mb-3 flex items-center justify-between gap-2 rounded-md border p-2"
		>
			<div class="px-2 text-xs">
				<strong>{{ provisionableCount }}</strong>
				of
				<strong>{{ rules.length }}</strong>
				rule{{ rules.length === 1 ? "" : "s" }} have a Graylog query available.
			</div>
			<n-button
				size="small"
				type="primary"
				secondary
				:disabled="loading || !provisionableCount"
				@click="showBulkModal = true"
			>
				<template #icon>
					<Icon :name="ProvisionIcon" />
				</template>
				Provision all
			</n-button>
		</div>

		<n-spin :show="loading">
			<div v-if="rules.length" class="grid grid-cols-1 gap-3">
				<RuleCard
					v-for="rule of rules"
					:key="rule.id"
					:rule
					embedded
					:provisioned="provisionedMap[rule.id] === true"
				/>
			</div>
			<n-empty
				v-else-if="!loading"
				description="No CoPilot Search rules cover this technique yet."
				class="h-40 justify-center"
			/>
		</n-spin>

		<n-modal
			v-model:show="showBulkModal"
			preset="card"
			:style="{ maxWidth: 'min(560px, 92vw)' }"
			title="Bulk Provision Graylog Alerts"
			:bordered="false"
			segmented
		>
			<BulkProvisionForm
				v-if="showBulkModal"
				:rule-ids="provisionableRules.map(r => r.id)"
				@close="showBulkModal = false"
				@success="onBulkSuccess"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type {
	BulkProvisionGraylogAlertResponse,
	MitreSubTechnique,
	MitreTechnique,
	RuleSummary
} from "@/types/copilot-searches"
import { NButton, NEmpty, NModal, NSpin, NTimeline, NTimelineItem, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import BulkProvisionForm from "./BulkProvisionForm.vue"
import RuleCard from "./RuleCard.vue"

const props = defineProps<{
	technique: MitreTechnique
	subTechnique?: MitreSubTechnique | null
}>()

const message = useMessage()
const rules = ref<RuleSummary[]>([])
const provisionedMap = ref<Record<string, boolean>>({})
const loading = ref(false)

const SEVERITY_RANK: Record<string, number> = {
	critical: 4,
	high: 3,
	medium: 2,
	low: 1
}

function sortBySeverity(list: RuleSummary[]): RuleSummary[] {
	return [...list].sort((a, b) => {
		const sa = SEVERITY_RANK[(a.severity || "").toLowerCase()] ?? 0
		const sb = SEVERITY_RANK[(b.severity || "").toLowerCase()] ?? 0
		if (sa !== sb) return sb - sa
		return (a.name || "").localeCompare(b.name || "")
	})
}

const ProvisionIcon = "carbon:add-alt"

const ruleIdsToLoad = computed<string[]>(() => {
	return props.subTechnique ? props.subTechnique.rule_ids : props.technique.rule_ids
})

const provisionableRules = computed<RuleSummary[]>(() => rules.value.filter(r => r.has_graylog_query))
const provisionableCount = computed(() => provisionableRules.value.length)

const showBulkModal = ref(false)

function onBulkSuccess(res: BulkProvisionGraylogAlertResponse) {
	const next = { ...provisionedMap.value }
	for (const r of res.results) {
		if (r.status === "provisioned" || r.status === "skipped") {
			next[r.rule_id] = true
		}
	}
	provisionedMap.value = next
}

async function loadRules() {
	const ids = ruleIdsToLoad.value
	if (!ids.length) {
		rules.value = []
		provisionedMap.value = {}
		return
	}
	loading.value = true
	provisionedMap.value = {}
	try {
		const [rulesRes, statusRes] = await Promise.all([
			Api.copilotSearches.getRulesByIds(ids),
			Api.copilotSearches.checkGraylogProvisioningStatus(ids).catch(() => null)
		])

		if (rulesRes.data?.success) {
			rules.value = sortBySeverity(rulesRes.data.rules || [])
			if (rulesRes.data.missing?.length) {
				message.warning(
					`Some rules could not be loaded (${rulesRes.data.missing.length}). Try refreshing the cache.`
				)
			}
		} else {
			message.warning(rulesRes.data?.message || "Failed to load rules for this technique")
		}

		if (statusRes?.data?.success && !statusRes.data.warning) {
			provisionedMap.value = statusRes.data.provisioned || {}
		}
	} catch (err) {
		const error = err as { response?: { data?: { message?: string } } }
		message.error(getApiErrorMessage(error as ApiError) || "Failed to load rules for this technique")
	} finally {
		loading.value = false
	}
}

watch(
	() => [props.technique.id, props.subTechnique?.id] as const,
	() => {
		loadRules()
	},
	{ immediate: true }
)

watch(
	() => [props.technique.id, props.subTechnique?.id] as const,
	() => {
		showBulkModal.value = false
	}
)
</script>
