<template>
	<div class="flex flex-wrap items-center gap-2">
		<AlertCreateExclusionRuleButton :alert @created="onCreated" />

		<!--
			Rules already created from this alert live behind one button rather than inline
			chips: the action row stays readable, and the list gets the room it needs in a
			modal (PICK 1). Hidden while there is nothing to show.
		-->
		<n-badge v-if="rules.length" :value="rules.length" :offset="[-6, 4]" type="warning">
			<n-button secondary :loading @click="showList = true">
				<template #icon>
					<Icon :name="ListIcon" />
				</template>
				Exclusion rules
			</n-button>
		</n-badge>

		<n-modal
			v-model:show="showList"
			display-directive="show"
			preset="card"
			:title="`Exclusion rules created from alert #${alert.id}`"
			:style="{ maxWidth: 'min(760px, 90vw)', minHeight: 'min(240px, 90vh)', maxHeight: '85vh' }"
			content-class="flex flex-col overflow-hidden p-0!"
			segmented
		>
			<n-scrollbar class="flex grow flex-col" content-class="grow" trigger="none">
				<div class="flex flex-col gap-3 p-5">
					<p class="text-secondary text-sm">
						Each rule points back here through its "From alert" badge. Deleting one from this list removes
						the rule, not the alert.
					</p>
					<ExclusionRuleItem
						v-for="rule of rules"
						:key="rule.id"
						:entity="rule"
						embedded
						@deleted="loadRules()"
						@updated="loadRules()"
					/>
				</div>
			</n-scrollbar>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts"
import type { ExclusionRule } from "@/types/incidentManagement/exclusion-rules"
import { NBadge, NButton, NModal, NScrollbar } from "naive-ui"
import { onBeforeMount, onBeforeUnmount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ExclusionRuleItem from "@/components/incidentManagement/exclusionRules/ExclusionRuleItem.vue"
import AlertCreateExclusionRuleButton from "./AlertCreateExclusionRuleButton.vue"

const props = defineProps<{ alert: Alert }>()
const emit = defineEmits<{
	(e: "updated", value: Alert): void
}>()

const { alert } = toRefs(props)

const ListIcon = "ic:outline-do-not-disturb-on"

const loading = ref(false)
const showList = ref(false)
const rules = ref<ExclusionRule[]>([])
let abort: AbortController | null = null

function loadRules() {
	abort?.abort()
	abort = new AbortController()
	loading.value = true

	Api.incidentManagement.exclusionRules
		.getExclusionRulesList({ pagination: { limit: 50 }, filters: { sourceAlertId: alert.value.id } }, abort.signal)
		.then(res => {
			if (res.data.success) {
				rules.value = res.data.exclusions ?? []
				if (!rules.value.length) showList.value = false
			}
		})
		.catch(() => {
			// A failed lookup only hides the list button; creating a rule still works.
		})
		.finally(() => {
			loading.value = false
		})
}

/**
 * Creation also left a comment on this alert server-side. Re-fetch the alert so the
 * Comments tab shows it without a page reload, and hand the fresh copy up.
 */
function onCreated() {
	loadRules()

	Api.incidentManagement.alerts.getAlert(alert.value.id).then(res => {
		const fresh = res.data.alerts?.[0]
		if (res.data.success && fresh) emit("updated", fresh)
	})
}

onBeforeMount(loadRules)
onBeforeUnmount(() => abort?.abort())
</script>
