<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="Create Exclusion Rule" :back-route="routeIncidentManagementSources()" />

		<n-alert v-if="sourceAlertId && draft && !draft.payload_available" type="warning">
			<span class="text-sm">
				Alert #{{ sourceAlertId }} kept its Sigma title and channel but not the event payload, so no field
				candidates can be offered. Add at least one field match by hand from the alert's details.
			</span>
		</n-alert>

		<n-spin :show="loadingDraft">
			<ExclusionRuleForm
				v-if="!sourceAlertId || draft"
				reset-on-submit
				:prefill
				:candidate-fields="draft?.fields"
				:source-alert-id
				@submitted="onSubmitted"
			/>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ExclusionRulePayload } from "@/api/endpoints/incidentManagement/exclusion-rules"
import type { ApiError } from "@/types/common"
import type { ExclusionRuleDraft } from "@/types/incidentManagement/exclusion-rules"
import { NAlert, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import ExclusionRuleForm from "@/components/incidentManagement/exclusionRules/ExclusionRuleForm.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const { routeIncidentManagementSources } = useNavigation()
const route = useRoute()
const message = useMessage()

/**
 * `?alert_id=<n>` turns this page into the deep-link form of the in-context flow (#934):
 * the same draft the alert's "Create exclusion rule" button uses, so a link pasted in a
 * ticket lands on a pre-filled, dry-run-checked form instead of a blank one.
 */
const sourceAlertId = computed(() => {
	const raw = Number(route.query.alert_id)
	return Number.isInteger(raw) && raw > 0 ? raw : undefined
})
const loadingDraft = ref(false)
const draft = ref<ExclusionRuleDraft | null>(null)
const prefill = ref<Partial<ExclusionRulePayload> | undefined>(undefined)

function loadDraft(alertId: number) {
	loadingDraft.value = true

	Api.incidentManagement.exclusionRules
		.getExclusionRuleDraft(alertId)
		.then(res => {
			if (res.data.success) {
				draft.value = res.data.draft
				prefill.value = {
					name: res.data.draft.name,
					description: res.data.draft.description,
					channel: res.data.draft.channel ?? "",
					title: res.data.draft.title ?? "",
					customer_code: res.data.draft.customer_code ?? undefined,
					enabled: true,
					source_alert_id: alertId,
					field_matches: Object.fromEntries(
						res.data.draft.fields.filter(f => f.suggested).map(f => [f.name, f.value])
					)
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDraft.value = false
		})
}

function onSubmitted() {
	routeIncidentManagementSources().navigate()
}

onBeforeMount(() => {
	if (sourceAlertId.value) loadDraft(sourceAlertId.value)
})
</script>
