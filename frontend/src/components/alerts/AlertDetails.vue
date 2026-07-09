<template>
	<n-spin :show="loading">
		<template v-if="resolvedAlert">
			<CardEntity>
				<template #headerMain>
					<span class="font-mono">#{{ resolvedAlert._id || resolvedAlert._source.id }}</span>
				</template>
				<template #headerExtra>
					{{ formatDate(resolvedAlert._source.timestamp_utc, dFormats.datetimesec) }}
				</template>

				<AlertOverview :alert="resolvedAlert" expanded />

				<template v-if="!hideActions" #footerExtra>
					<AlertActions
						:alert="resolvedAlert"
						:soc-alert-field="socAlertCreationField"
						size="small"
						@updated-url="resolvedAlert._source.alert_url = $event"
						@updated-id="resolvedAlert._source.alert_id = $event"
						@updated-ask-message="resolvedAlert._source.ask_socfortress_message = $event"
					/>
				</template>
			</CardEntity>

			<n-card class="mt-4 overflow-hidden" content-class="p-0!">
				<AlertDetailTabs :alert="resolvedAlert" />
			</n-card>
		</template>

		<n-empty v-else-if="!loading" description="Alert not found" class="h-48 justify-center" />
	</n-spin>
</template>

<script setup lang="ts">
import type { SocAlertField } from "./type.d"
import type { Alert } from "@/types/alerts"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { NCard, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, inject, onBeforeMount, onBeforeUnmount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import AlertDetailTabs from "./AlertDetailTabs.vue"
import AlertOverview from "./AlertOverview.vue"

const props = defineProps<{
	alert?: Alert
	indexName?: string
	alertId?: string
	hideActions?: boolean
}>()

const { alert, indexName, alertId, hideActions } = toRefs(props)

const AlertActions = defineAsyncComponent(() => import("./AlertActions.vue"))

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const fetchedAlert = ref<Alert | null>(null)
let abortController: AbortController | null = null

const socAlertCreationField = ref(inject<SocAlertField>("soc-alert-creation-field", "alert_url"))

const resolvedAlert = computed(() => alert.value ?? fetchedAlert.value)

function load() {
	if (alert.value || !indexName.value || !alertId.value) return

	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.alerts
		.getById({ index_name: indexName.value, alert_id: alertId.value }, abortController.signal)
		.then(res => {
			if (res.data.success && res.data.alert) {
				fetchedAlert.value = res.data.alert as Alert
			} else {
				fetchedAlert.value = null
				message.warning(res.data?.message || "Alert not found")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				fetchedAlert.value = null
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	load()
})

watch([indexName, alertId], () => {
	fetchedAlert.value = null
	load()
})

onBeforeUnmount(() => {
	abortController?.abort()
})

defineExpose({ reload: load })
</script>
