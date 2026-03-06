<template>
	<div class="flex flex-col gap-2">
		<div class="flex items-center gap-2">
			<PlatformBadge :platform />
			<SeverityBadge :severity />
		</div>
		<h3 class="font-semibold">{{ name }}</h3>
		<p class="text-sm opacity-70">{{ description }}</p>
	</div>
</template>

<script setup lang="ts">
import type { RuleDetail, RuleSummary } from "@/types/copilotSearches.d"
import { useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import PlatformBadge from "@/components/common/PlatformBadge.vue"
import SeverityBadge from "./SeverityBadge.vue"

const props = defineProps<{
	ruleId?: string
	ruleDetail?: RuleDetail
	ruleSummary?: RuleSummary
}>()

const message = useMessage()
const loading = ref(false)
const ruleDetail = ref<RuleDetail | null>(null)
const ruleSummary = ref<RuleSummary | null>(null)

const platform = computed(() => ruleDetail.value?.tags?.asset_type || ruleSummary.value?.platform || "unknown")
const severity = computed(() => ruleDetail.value?.response?.severity || ruleSummary.value?.severity || "medium")
const name = computed(() => ruleDetail.value?.name || ruleSummary.value?.name || "")
const description = computed(() => ruleDetail.value?.description || ruleSummary.value?.description || "")

async function loadRule(ruleId: string) {
	loading.value = true

	try {
		const res = await Api.copilotSearches.getRuleById(ruleId)
		if (res.data.success) {
			ruleDetail.value = res.data.rule
		} else {
			message.error(res.data?.message || "Failed to load rule details")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load rule details")
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	if (props.ruleDetail) {
		ruleDetail.value = props.ruleDetail
	} else if (props.ruleSummary) {
		ruleSummary.value = props.ruleSummary
	} else if (props.ruleId) {
		loadRule(props.ruleId)
	} else {
		message.error("No rule data or rule ID provided")
	}
})
</script>
