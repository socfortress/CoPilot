<template>
	<section class="border-default bg-default flex flex-col gap-3 rounded-lg border px-4 py-3" data-testid="talon-analysis-offer">
		<header class="flex flex-wrap items-center gap-2">
			<Icon name="carbon:ai-launch" :size="16" class="text-secondary" />
			<h4 class="m-0 text-sm font-semibold">{{ $t("talonChat.analysisOffer.title") }}</h4>
		</header>

		<p class="m-0 text-sm">{{ $t("talonChat.analysisOffer.text", { id: alertId }) }}</p>

		<div class="flex flex-wrap items-center gap-3">
			<RouterLink :to="{ name: 'AlertDetails', params: { id: alertId } }" class="text-primary text-sm" data-testid="talon-analysis-offer-alert">
				{{ $t("talonChat.analysisOffer.openAlert") }}
			</RouterLink>

			<!-- The alert's own "Run AI analysis" button and its gates (#1215). -->
			<AiAnalysisRequestButton
				v-if="allowed"
				:has-analysis="!!analysis?.has_analysis"
				:in-progress
				:requesting
				@request="requestAnalysis"
			/>
			<n-spin v-else-if="loading" size="small" />
		</div>

		<p v-if="loadFailed" class="text-secondary m-0 text-xs" data-testid="talon-analysis-offer-load-error">
			{{ $t("talonChat.analysisOffer.loadFailed") }}
		</p>
		<p v-else-if="!loading && !allowed" class="text-secondary m-0 text-xs" data-testid="talon-analysis-offer-not-allowed">
			{{ $t("talonChat.analysisOffer.notAllowed") }}
		</p>

		<n-alert v-if="requested" type="success" :bordered="false" data-testid="talon-analysis-offer-requested">
			{{ $t("talonChat.analysisOffer.requested") }}
		</n-alert>
		<n-alert v-if="requestError" type="warning" :bordered="false" data-testid="talon-analysis-offer-error">
			{{ requestError }}
		</n-alert>
	</section>
</template>

<script setup lang="ts">
import type { AiAlertAnalysis } from "@/types/aiReports"
import type { ApiError } from "@/types/common"
import { NAlert, NSpin } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { RouterLink } from "vue-router"
import Api from "@/api"
import AiAnalysisRequestButton from "@/components/alerts/AlertDetails/AiAnalysisRequestButton.vue"
import { STALE_INVESTIGATION_MS, utcMillis } from "@/components/alerts/AlertDetails/aiInvestigation"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { getApiErrorMessage } from "@/utils"

/**
 * Talon's offer to analyse an alert (`offer_ai_analysis`, talon-analyst D97 Q5). Talon starts
 * nothing: the button is the alert's own "Run AI analysis" (#1215), through the same portal route
 * and its gates (the customer's switch, the cooldown, the daily limit, read-only), shown only when
 * the alert's analysis says the user may ask (`can_request`) and the availability agrees.
 */
const { alertId, canRequest = false } = defineProps<{
	alertId: number
	canRequest?: boolean
}>()

const { t } = useI18n()

const analysis = ref<AiAlertAnalysis | null>(null)
const loadFailed = ref(false)
const { loading, run } = useLatestRequest()
const requesting = ref(false)
const requested = ref(false)
const requestError = ref<string | null>(null)

const allowed = computed(() => canRequest && !!analysis.value?.enabled && !!analysis.value?.can_request)

const inProgress = computed(() => {
	if (requested.value) return true
	const job = analysis.value?.investigation
	return (
		!!job && ["pending", "running"].includes(job.status) && Date.now() - utcMillis(job.created_at) < STALE_INVESTIGATION_MS
	)
})

function load() {
	loadFailed.value = false
	if (!canRequest) return Promise.resolve()
	return run(
		async signal => {
			analysis.value = (await Api.aiReports.getAlertAnalysis(alertId, signal)).data
		},
		() => {
			loadFailed.value = true
		}
	)
}

async function requestAnalysis() {
	requesting.value = true
	requestError.value = null
	try {
		await Api.aiReports.requestAnalysis(alertId)
		requested.value = true
	} catch (err) {
		// The alert page's own wording of the refusal (#1215): its route carries no code.
		requestError.value = getApiErrorMessage(err as ApiError) || t("alerts.aiReport.requestFailed")
		if ((err as ApiError).response?.status === 409) await load()
	} finally {
		requesting.value = false
	}
}

watch(
	() => [alertId, canRequest],
	() => {
		analysis.value = null
		requested.value = false
		requestError.value = null
		load()
	},
	{ immediate: true }
)
</script>
