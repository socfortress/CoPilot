<template>
	<n-drawer v-model:show="showLocal" :width="drawerWidth" placement="right">
		<n-drawer-content :title="drawerTitle" closable>
			<template v-if="technique">
				<div class="mb-3 flex flex-col gap-1">
					<div class="text-secondary text-sm">
						<a v-if="technique.url" :href="technique.url" target="_blank" rel="noopener">
							{{ technique.id }} — view on attack.mitre.org ↗
						</a>
					</div>
					<div v-if="subTechnique" class="text-secondary text-sm">
						Sub-technique:
						<a v-if="subTechnique.url" :href="subTechnique.url" target="_blank" rel="noopener">
							{{ subTechnique.id }} {{ subTechnique.name }} ↗
						</a>
						<span v-else>{{ subTechnique.id }} {{ subTechnique.name }}</span>
					</div>
				</div>

				<div
					v-if="provisionableCount > 0"
					class="border-default bg-secondary mb-3 flex items-center justify-between gap-2 rounded-md border p-2"
				>
					<div class="text-secondary text-xs">
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
			</template>
		</n-drawer-content>

		<BulkProvisionModal
			v-model:show="showBulkModal"
			:rule-ids="provisionableRules.map(r => r.id)"
			@success="onBulkSuccess"
		/>
	</n-drawer>
</template>

<script setup lang="ts">
import type {
	BulkProvisionGraylogAlertResponse,
	MitreSubTechnique,
	MitreTechnique,
	RuleSummary
} from "@/types/copilotSearches.d"
import { NButton, NDrawer, NDrawerContent, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import BulkProvisionModal from "./BulkProvisionModal.vue"
import RuleCard from "./RuleCard.vue"

const props = defineProps<{
	show: boolean
	technique: MitreTechnique | null
	subTechnique?: MitreSubTechnique | null
}>()

const emit = defineEmits<{
	(e: "update:show", value: boolean): void
}>()

const showLocal = computed({
	get: () => props.show,
	set: v => emit("update:show", v)
})

const message = useMessage()
const rules = ref<RuleSummary[]>([])
const provisionedMap = ref<Record<string, boolean>>({})
const loading = ref(false)
const drawerWidth = computed(() => Math.min(820, window.innerWidth - 40))

// Severity ordering: critical > high > medium > low > unknown
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

const drawerTitle = computed(() => {
	if (!props.technique) return "Technique"
	if (props.subTechnique) return `${props.subTechnique.id} ${props.subTechnique.name}`
	return `${props.technique.id} ${props.technique.name}`
})

const ruleIdsToLoad = computed<string[]>(() => {
	if (!props.technique) return []
	return props.subTechnique ? props.subTechnique.rule_ids : props.technique.rule_ids
})

const provisionableRules = computed<RuleSummary[]>(() => rules.value.filter(r => r.has_graylog_query))
const provisionableCount = computed(() => provisionableRules.value.length)

const showBulkModal = ref(false)

function onBulkSuccess(res: BulkProvisionGraylogAlertResponse) {
	// Reflect new "in Graylog" state immediately on the visible rules list,
	// so the chip pops the moment the result modal closes.
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
		// Load rules and provisioning status in parallel — provisioning is best-effort:
		// if Graylog is unreachable the chip just doesn't show, no error to the user.
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
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load rules for this technique")
	} finally {
		loading.value = false
	}
}

watch(
	() => [props.show, ruleIdsToLoad.value] as const,
	([open]) => {
		if (open) loadRules()
	},
	{ immediate: true, deep: true }
)

// Close the bulk modal automatically when the drawer's context changes —
// the modal itself resets its own internal state on next open.
watch(
	() => [props.technique?.id, props.subTechnique?.id] as const,
	() => {
		showBulkModal.value = false
	}
)
</script>
