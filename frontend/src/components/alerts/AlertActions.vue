<template>
	<div class="flex flex-wrap justify-end gap-2">
		<n-button v-if="socAlertFieldValue" type="success" secondary :size="size" @click.stop="gotoSocAlertUrl()">
			<template #icon>
				<Icon :name="ViewIcon"></Icon>
			</template>
			View SOC Alert
		</n-button>
		<n-button
			v-if="!socAlertFieldValue"
			:loading="loadingSocAlert"
			type="warning"
			secondary
			:size="size"
			@click.stop="createAlert()"
		>
			<template #icon>
				<Icon :name="DangerIcon"></Icon>
			</template>
			Create SOC Alert
		</n-button>
		<n-button v-if="alertAskMessage" type="success" secondary :size="size" @click.stop="showSocResponse = true">
			<template #icon>
				<Icon :name="ViewIcon"></Icon>
			</template>
			View SOCFortress Response
		</n-button>
		<n-button
			v-if="isAskVisible"
			:loading="loadingAskSoc"
			type="warning"
			secondary
			:size="size"
			@click.stop="askSOCFortress()"
		>
			<template #icon>
				<Icon :name="AskIcon"></Icon>
			</template>
			Ask SOCFortress
		</n-button>
		<n-button
			v-if="isWazuhRulesVisible"
			:loading="loadingWazuhRuleExclude"
			secondary
			:size="size"
			@click.stop="wazuhManagerRuleExclude()"
		>
			<template #icon>
				<Icon :name="RulesIcon"></Icon>
			</template>
			Exclude Rule in Wazuh
		</n-button>

		<n-modal
			v-model:show="showSocResponse"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			title="SOCFortress Response"
			:bordered="false"
			segmented
		>
			<n-input
				:value="alertAskMessage"
				type="textarea"
				readonly
				placeholder="SOCFortress Response"
				size="large"
				:autosize="{
					minRows: 3
				}"
			/>
		</n-modal>

		<n-modal
			v-model:show="showWazuhRuleExclude"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			title="Recommended exclusion for a Wazuh Rule"
			:bordered="false"
			content-class="!p-0"
			segmented
		>
			<AlertWazuhRules v-if="wazuhRuleData" :data="wazuhRuleData" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SocAlertField } from "./type.d"
import type { Alert, WazuhRuleExclude } from "@/types/alerts.d"
import { NButton, NInput, NModal, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import AlertWazuhRules from "./AlertWazuhRules.vue"

const { alert, size, socAlertField } = defineProps<{
	alert: Alert
	size?: "tiny" | "small" | "medium" | "large"
	socAlertField: SocAlertField
}>()

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(e: "updatedUrl", value: string): void
	(e: "updatedId", value: number): void
	(e: "updatedAskMessage", value: string): void
}>()

const DangerIcon = "majesticons:exclamation-line"
const AskIcon = "majesticons:question-mark-circle-line"
const ViewIcon = "iconoir:eye-solid"
const RulesIcon = "carbon:rule-cancelled"

const router = useRouter()
const message = useMessage()
const showSocResponse = ref(false)
const showWazuhRuleExclude = ref(false)
const loadingSocAlert = ref(false)
const loadingAskSoc = ref(false)
const loadingWazuhRuleExclude = ref(false)
const loading = computed(() => loadingSocAlert.value || loadingAskSoc.value || loadingWazuhRuleExclude.value)

const alertUrl = ref("")
const alertId = ref(0)
const alertAskMessage = ref("")
const wazuhRuleData = ref<WazuhRuleExclude | null>(null)

const socAlertFieldValue = computed(() => (socAlertField === "alert_id" ? alertId.value : alertUrl.value))

const isAskVisible = computed(() => alert._source?.rule_group3 === "sigma" && !alertAskMessage.value)
const isWazuhRulesVisible = computed(() => alert._source)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

watch(alertUrl, val => {
	if (val) {
		emit("updatedUrl", val)
	}
})

watch(alertId, val => {
	if (val) {
		emit("updatedId", val)
	}
})

watch(alertAskMessage, val => {
	if (val) {
		emit("updatedAskMessage", val)
	}
})

function gotoSocAlertUrl() {
	if (socAlertField === "alert_url") {
		window.open(alertUrl.value, "_blank")
	} else if (socAlertField === "alert_id") {
		router.push({ name: "IncidentManagement-Alerts", query: alertId.value ? { alert_id: alertId.value } : {} })
	}
}

function askSOCFortress() {
	loadingAskSoc.value = true

	Api.askSocfortress
		.create(alert._index, alert._id)
		.then(res => {
			if (res.data.success) {
				res.data.message && (alertAskMessage.value = res.data.message)
				message.success("Asked SOCFortress Sigma.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAskSoc.value = false
		})
}

function wazuhManagerRuleExclude() {
	if (wazuhRuleData.value) {
		showWazuhRuleExclude.value = true
		return
	}

	loadingWazuhRuleExclude.value = true

	Api.alerts
		.wazuhManagerRuleExclude(alert._source)
		.then(res => {
			if (res.data.success) {
				wazuhRuleData.value = {
					wazuh_rule: res.data.wazuh_rule,
					explanation: res.data.explanation
				}
				showWazuhRuleExclude.value = true
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingWazuhRuleExclude.value = false
		})
}

function createAlert() {
	loadingSocAlert.value = true

	Api.alerts
		.create(alert._index, alert._id)
		.then(res => {
			if (res.data.success) {
				res.data.alert_url && (alertUrl.value = res.data.alert_url)
				res.data.alert_id && (alertId.value = res.data.alert_id)
				message.success(res.data?.message || "SOC Alert created.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingSocAlert.value = false
		})
}

onBeforeMount(() => {
	alertUrl.value = alert._source.alert_url || ""
	alertId.value = alert._source.alert_id || 0
	alertAskMessage.value = alert._source.ask_socfortress_message || ""
})
</script>
