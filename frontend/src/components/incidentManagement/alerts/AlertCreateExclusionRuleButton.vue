<template>
	<n-button secondary type="warning" :loading="loadingDraft" @click="openDialog()">
		<template #icon>
			<Icon :name="ExclusionIcon" />
		</template>
		Create exclusion rule
	</n-button>

	<n-modal
		v-model:show="showDialog"
		display-directive="show"
		preset="card"
		title="Create exclusion rule from alert"
		:style="{ maxWidth: 'min(760px, 90vw)', minHeight: 'min(420px, 90vh)', maxHeight: '85vh' }"
		content-class="flex flex-col overflow-hidden px-2! py-0!"
		segmented
	>
		<n-scrollbar class="flex grow flex-col" content-class="grow" trigger="none">
			<div class="flex flex-col gap-4 px-5 py-5">
				<p class="text-secondary text-sm">
					Pre-filled from this alert's Velociraptor Sigma payload
					<template v-if="draft?.computer">
						(host
						<code>{{ draft.computer }}</code>
						)
					</template>
					. Channel and title match exactly; tick the fields that identify the benign activity and complete
					the justification. The rule is checked live against this alert as you edit it.
				</p>

				<n-alert v-if="draft && !draft.payload_available" type="warning">
					<span class="text-sm">
						This alert kept its Sigma title and channel but not the event payload, so no field candidates
						can be offered. Add at least one field match by hand from the alert's details.
					</span>
				</n-alert>

				<ExclusionRuleForm
					v-if="draft && prefill"
					:prefill
					:candidate-fields="draft.fields"
					:source-alert-id="alert.id"
					@submitted="onSubmitted"
				/>
			</div>
		</n-scrollbar>
	</n-modal>
</template>

<script setup lang="ts">
import type { ExclusionRulePayload } from "@/api/endpoints/incidentManagement/exclusion-rules"
import type { ApiError } from "@/types/common"
import type { Alert } from "@/types/incidentManagement/alerts"
import type { ExclusionRule, ExclusionRuleDraft } from "@/types/incidentManagement/exclusion-rules"
import { NAlert, NButton, NModal, NScrollbar, useMessage } from "naive-ui"
import { h, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ExclusionRuleForm from "@/components/incidentManagement/exclusionRules/ExclusionRuleForm.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ alert: Alert }>()
const emit = defineEmits<{
	(e: "created", value: ExclusionRule): void
}>()

const { alert } = toRefs(props)

const ExclusionIcon = "ic:outline-do-not-disturb-on"

const message = useMessage()
const { routeIncidentManagementExclusionRule } = useNavigation()
const loadingDraft = ref(false)
const showDialog = ref(false)
const draft = ref<ExclusionRuleDraft | null>(null)
const prefill = ref<Partial<ExclusionRulePayload> | null>(null)

/**
 * The draft is rebuilt on every open rather than cached: the analyst may have edited
 * comments meanwhile, and a stale prefill is exactly the kind of "looks right, never
 * matches" rule this feature exists to prevent.
 */
function openDialog() {
	loadingDraft.value = true

	Api.incidentManagement.exclusionRules
		.getExclusionRuleDraft(alert.value.id)
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
					source_alert_id: alert.value.id,
					field_matches: Object.fromEntries(
						res.data.draft.fields.filter(f => f.suggested).map(f => [f.name, f.value])
					)
				}
				showDialog.value = true
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

function onSubmitted(rule: ExclusionRule) {
	showDialog.value = false
	emit("created", rule)

	const route = routeIncidentManagementExclusionRule(rule.id)
	message.success(
		() =>
			h("div", { class: "flex items-center gap-3" }, [
				h("span", `Exclusion rule "${rule.name}" created`),
				h(
					NButton,
					{ size: "tiny", secondary: true, onClick: () => route.navigate() },
					{ default: () => "Open rule" }
				)
			]),
		{ duration: 8000, closable: true }
	)
}
</script>
