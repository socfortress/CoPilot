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

				<n-spin :show="loading">
					<div v-if="rules.length" class="grid grid-cols-1 gap-3">
						<RuleCard v-for="rule of rules" :key="rule.id" :rule embedded />
					</div>
					<n-empty
						v-else-if="!loading"
						description="No CoPilot Search rules cover this technique yet."
						class="h-40 justify-center"
					/>
				</n-spin>
			</template>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import type { MitreSubTechnique, MitreTechnique, RuleSummary } from "@/types/copilotSearches.d"
import { NDrawer, NDrawerContent, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
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
const loading = ref(false)
const drawerWidth = computed(() => Math.min(820, window.innerWidth - 40))

const drawerTitle = computed(() => {
	if (!props.technique) return "Technique"
	if (props.subTechnique) return `${props.subTechnique.id} ${props.subTechnique.name}`
	return `${props.technique.id} ${props.technique.name}`
})

const ruleIdsToLoad = computed<string[]>(() => {
	if (!props.technique) return []
	return props.subTechnique ? props.subTechnique.rule_ids : props.technique.rule_ids
})

async function loadRules() {
	const ids = ruleIdsToLoad.value
	if (!ids.length) {
		rules.value = []
		return
	}
	loading.value = true
	try {
		const res = await Api.copilotSearches.getRulesByIds(ids)
		if (res.data?.success) {
			rules.value = res.data.rules || []
			if (res.data.missing?.length) {
				message.warning(
					`Some rules could not be loaded (${res.data.missing.length}). Try refreshing the cache.`
				)
			}
		} else {
			message.warning(res.data?.message || "Failed to load rules for this technique")
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
</script>
