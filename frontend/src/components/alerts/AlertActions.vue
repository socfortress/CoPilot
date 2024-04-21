<template>
	<div class="alert-actions flex flex-col gap-2 justify-end">
		<n-button type="success" secondary :size="size" v-if="alertUrl" tag="a" :href="alertUrl" target="_blank">
			<template #icon><Icon :name="ViewIcon"></Icon></template>
			View SOC Alert
		</n-button>
		<n-button
			:loading="loadingSocAlert"
			type="warning"
			secondary
			:size="size"
			@click="createAlert()"
			v-if="!alertUrl"
		>
			<template #icon><Icon :name="DangerIcon"></Icon></template>
			Create SOC Alert
		</n-button>
		<n-button type="success" secondary :size="size" v-if="alertAskMessage" @click="showSocResponse = true">
			<template #icon><Icon :name="ViewIcon"></Icon></template>
			View SOCFortress Response
		</n-button>
		<n-button
			:loading="loadingAskSoc"
			type="warning"
			secondary
			:size="size"
			@click="askSOCFortress()"
			v-if="isAskVisible"
		>
			<template #icon><Icon :name="AskIcon"></Icon></template>
			Ask SOCFortress
		</n-button>
		<n-button
			:loading="loadingWazuhRuleExclude"
			secondary
			:size="size"
			@click="wazuhManagerRuleExclude()"
			v-if="isWazuhRulesVisible"
		>
			<template #icon><Icon :name="RulesIcon"></Icon></template>
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
			<AlertWazuhRules :data="wazuhRuleData" v-if="wazuhRuleData" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, watch } from "vue"
import { NButton, NInput, NModal, useMessage } from "naive-ui"
import AlertWazuhRules from "./AlertWazuhRules.vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import type { Alert, WazuhRuleExclude } from "@/types/alerts.d"

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
	(e: "updatedUrl", value: string): void
	(e: "updatedAskMessage", value: string): void
}>()

const { alert, size } = defineProps<{ alert: Alert; size?: "tiny" | "small" | "medium" | "large" }>()

const DangerIcon = "majesticons:exclamation-line"
const AskIcon = "majesticons:question-mark-circle-line"
const ViewIcon = "iconoir:eye-alt"
const RulesIcon = "carbon:rule-cancelled"

const message = useMessage()
const showSocResponse = ref(false)
const showWazuhRuleExclude = ref(false)
const loadingSocAlert = ref(false)
const loadingAskSoc = ref(false)
const loadingWazuhRuleExclude = ref(false)
const loading = computed(() => loadingSocAlert.value || loadingAskSoc.value || loadingWazuhRuleExclude.value)

const alertUrl = ref("")
const alertAskMessage = ref("")
const wazuhRuleData = ref<WazuhRuleExclude | null>(null)

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

watch(alertAskMessage, val => {
	if (val) {
		emit("updatedAskMessage", val)
	}
})

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
	alertAskMessage.value = alert._source.ask_socfortress_message || ""
})
</script>
