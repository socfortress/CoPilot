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
import { NCard, NEmpty, NSpin } from "naive-ui"
import { defineAsyncComponent, inject, ref, toRefs } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import AlertDetailTabs from "./AlertDetailTabs.vue"
import AlertOverview from "./AlertOverview.vue"

const props = defineProps<{
	alert?: Alert
	indexName?: string
	alertId?: string
	hideActions?: boolean
}>()

const { hideActions } = toRefs(props)

const AlertActions = defineAsyncComponent(() => import("./AlertActions.vue"))

const dFormats = useSettingsStore().dateFormat

const socAlertCreationField = ref(inject<SocAlertField>("soc-alert-creation-field", "alert_url"))

const { loading, entity: resolvedAlert, reload } = useEntityDetails<Alert, string>({
	entity: () => props.alert,
	id: () => (props.indexName && props.alertId ? `${props.indexName}|${props.alertId}` : null),
	fetch: (_id, signal) =>
		Api.alerts
			.getById({ index_name: props.indexName as string, alert_id: props.alertId as string }, signal)
			.then(res => ({
				entity: res.data.success ? ((res.data.alert as Alert) ?? null) : null,
				message: res.data.message
			})),
	notFoundMessage: "Alert not found",
	errorMessage: "An error occurred. Please try again later."
})

defineExpose({ reload })
</script>
