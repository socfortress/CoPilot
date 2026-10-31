<template>
	<div class="flex flex-col gap-4" data-testid="customer-questions">
		<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
			<div class="flex min-w-0 flex-col gap-1">
				<h1 class="text-xl font-semibold">Customer questions</h1>
				<p class="text-secondary m-0 max-w-prose text-sm">
					What Customer Portal users asked the SOC about their alerts and cases. A comment from the SOC on the
					case or alert answers it; mark it answered when the reply went another way.
				</p>
			</div>
			<n-radio-group
				:value="status"
				size="small"
				data-testid="customer-questions-status"
				@update:value="(value: StatusFilter) => setStatus(value)"
			>
				<n-radio-button value="open">Open{{ counts ? ` (${counts.open})` : "" }}</n-radio-button>
				<n-radio-button value="answered">
					Answered{{ counts ? ` (${counts.total - counts.open})` : "" }}
				</n-radio-button>
				<n-radio-button value="all">All{{ counts ? ` (${counts.total})` : "" }}</n-radio-button>
			</n-radio-group>
		</header>

		<n-alert v-if="error" type="error" :bordered="false" data-testid="customer-questions-error">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<span>{{ error }}</span>
				<n-button size="small" secondary @click="load()">Try again</n-button>
			</div>
		</n-alert>

		<n-spin v-else :show="loading">
			<div
				v-if="!requests.length && !loading"
				class="border-default bg-default flex flex-col items-center gap-2 rounded-lg border px-6 py-12 text-center"
				data-testid="customer-questions-empty"
			>
				<Icon name="carbon:help" :size="26" class="text-tertiary" />
				<p class="m-0 font-semibold">
					{{ status === "open" ? "No question waiting for the SOC" : "No customer questions" }}
				</p>
				<p class="text-secondary m-0 text-sm">
					Questions appear here once a customer's portal users may ask the SOC (Customers → customer → Ask the
					SOC).
				</p>
			</div>

			<ul v-else class="m-0 flex list-none flex-col gap-3 p-0">
				<li
					v-for="request of requests"
					:key="request.id"
					class="border-default bg-default flex flex-col gap-2 rounded-lg border px-4 py-3"
					:data-status="request.status"
					data-testid="customer-question-row"
				>
					<div class="flex flex-wrap items-center justify-between gap-2">
						<div class="flex min-w-0 flex-wrap items-center gap-2 text-sm">
							<n-tag :type="URGENCY_TAG[request.urgency]" size="small" :bordered="false">
								{{ URGENCY_LABELS[request.urgency] }}
							</n-tag>
							<n-tag
								v-if="request.drafted_with_talon"
								size="small"
								:bordered="false"
								title="Talon drafted this question in the portal chat; the customer edited and sent it"
								data-testid="customer-question-drafted-with-talon"
							>
								Drafted with Talon
							</n-tag>
							<n-button
								v-if="questionTarget(request)"
								text
								type="primary"
								class="min-w-0"
								data-testid="customer-question-target"
								@click="openTarget(request)"
							>
								<span class="truncate">
									<bdi>{{ targetLabel(request) }}</bdi>
								</span>
							</n-button>
							<span v-else class="text-secondary">{{ targetLabel(request) }}</span>
							<code class="text-secondary text-xs">{{ request.customer_code }}</code>
						</div>
						<n-button
							v-if="request.status === 'open'"
							size="small"
							secondary
							:loading="marking === request.id"
							data-testid="customer-question-mark"
							@click="markAnswered(request)"
						>
							Mark answered
						</n-button>
						<span
							v-else
							class="text-success flex items-center gap-1 text-xs"
							data-testid="customer-question-done"
						>
							<Icon name="carbon:checkmark-outline" :size="14" />
							{{ answeredText(request) }}
						</span>
					</div>
					<p class="text-default m-0 text-sm whitespace-pre-wrap" data-testid="customer-question-text">
						<bdi>{{ request.question }}</bdi>
					</p>
					<div class="text-secondary text-xs">
						Asked by
						<bdi>{{ request.requested_by }}</bdi>
						· {{ formatDate(request.requested_at, dFormats.datetime, { tz: true }) }}
						<template v-if="request.answered_at">
							· answered {{ formatDate(request.answered_at, dFormats.datetime, { tz: true }) }}
						</template>
					</div>
				</li>
			</ul>
		</n-spin>

		<n-modal
			v-model:show="showTarget"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(482px, 90vh)', overflow: 'hidden' }"
			@after-leave="afterClose()"
		>
			<n-card
				content-class="flex flex-col p-0!"
				:title="opened ? targetLabel(opened) : ''"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="showTarget = false"
			>
				<template #header-extra>
					<ModalPageButton
						:route="openedRoute"
						:label="openedTarget?.entity === 'case' ? 'Open the case\'s page' : 'Open the alert\'s page'"
						@navigate="showTarget = false"
					/>
				</template>
				<CaseDetails v-if="openedTarget?.entity === 'case'" :case-id="openedTarget.id" />
				<AlertDetails v-else-if="openedTarget?.entity === 'alert'" :alert-id="openedTarget.id" />
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SocRequest } from "@/types/soc-requests"
import { NAlert, NButton, NCard, NModal, NRadioButton, NRadioGroup, NSpin, NTag, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ModalPageButton from "@/components/common/ModalPageButton.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useNavigation } from "@/composables/useNavigation"
import { useOpenCustomerQuestions } from "@/composables/useOpenCustomerQuestions"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { answeredText, questionTarget, targetLabel, URGENCY_LABELS, URGENCY_TAG } from "./customerQuestions"

/**
 * Incidents → Customer questions (#1305): what portal users asked the SOC, open first. The status is
 * in the URL (`?status=answered|all`, the default `open` left out); the customers are the global
 * filter's. A target opens its case or alert in a modal whose header leads to its page.
 */

type StatusFilter = "open" | "answered" | "all"

const CaseDetails = defineAsyncComponent(() => import("@/components/incidentManagement/cases/CaseDetails.vue"))
const AlertDetails = defineAsyncComponent(() => import("@/components/incidentManagement/alerts/AlertDetails.vue"))

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const { globalCustomerCodes, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()
const { routeIncidentManagementCases, routeIncidentManagementAlerts } = useNavigation()
const { invalidate } = useOpenCustomerQuestions()

const requests = ref<SocRequest[]>([])
const counts = ref<{ total: number; open: number } | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const marking = ref<number | null>(null)
const customerCodes = ref<string[]>([...globalCustomerCodes.value])
let latest = 0

const status = computed<StatusFilter>(() => {
	const value = route.query.status
	return value === "answered" || value === "all" ? value : "open"
})

function setStatus(value: StatusFilter) {
	const { status: _status, ...rest } = route.query
	router.replace({ query: value === "open" ? rest : { ...rest, status: value } })
}

async function load() {
	const request = ++latest
	loading.value = true
	error.value = null
	try {
		const res = await Api.socRequests.list({
			status: status.value === "all" ? null : status.value,
			customerCodes: customerCodes.value
		})
		if (request !== latest) return
		requests.value = res.data.requests ?? []
		counts.value = { total: res.data.total, open: res.data.open }
	} catch (err) {
		if (request !== latest) return
		error.value = getApiErrorMessage(err as ApiError) || "Could not load the customer questions."
	} finally {
		if (request === latest) loading.value = false
	}
}

async function markAnswered(request: SocRequest) {
	marking.value = request.id
	try {
		await Api.socRequests.markAnswered(request.id)
		message.success("Question marked answered")
		invalidate()
		await load()
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Could not mark the question answered.")
	} finally {
		marking.value = null
	}
}

// The case or alert a question is on, in a modal.
const showTarget = ref(false)
const opened = ref<SocRequest | null>(null)
const openedTarget = computed(() => (opened.value ? questionTarget(opened.value) : null))
const openedRoute = computed(() => {
	const target = openedTarget.value
	if (!target) return null
	return target.entity === "case" ? routeIncidentManagementCases(target.id) : routeIncidentManagementAlerts(target.id)
})

function openTarget(request: SocRequest) {
	opened.value = request
	showTarget.value = true
}

// A comment written in the modal may have answered it.
function afterClose() {
	opened.value = null
	invalidate()
	load()
}

watch(status, () => {
	load()
})

onGlobalCustomerFilterChange(codes => {
	customerCodes.value = [...codes]
	load()
})

onBeforeMount(() => {
	load()
})
</script>
