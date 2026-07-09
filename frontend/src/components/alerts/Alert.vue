<template>
	<div>
		<CardEntity hoverable :embedded class="@container">
			<template #headerMain>#{{ alert._id || alert._source.id }}</template>
			<template #headerExtra>
				{{ formatDate(alert._source.timestamp_utc, dFormats.datetimesec) }}
			</template>
			<template #default>
				<AlertOverview :alert part="meta" />
			</template>
			<template v-if="alert._id" #mainExtra>
				<AlertOverview :alert part="badges" />
			</template>
			<template v-if="!hideActions || !hideOpen" #footerExtra>
				<div class="flex flex-wrap items-center justify-end gap-2">
					<EntityDetailsButton
						v-if="!hideOpen && alertOpenUrl"
						size="small"
						:url="alertOpenUrl"
						@view="showDetails = true"
					/>
					<AlertActions
						v-if="!hideActions"
						:alert
						:soc-alert-field="socAlertCreationField"
						size="small"
						@start-loading="loading = true"
						@stop-loading="loading = false"
						@updated-url="alert._source.alert_url = $event"
						@updated-id="alert._source.alert_id = $event"
						@updated-ask-message="alert._source.ask_socfortress_message = $event"
					/>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Alert: ${alert._id || alert._source.id}`"
			:bordered="false"
			segmented
		>
			<AlertDetailTabs :alert />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SocAlertField } from "./type.d"
import type { Alert } from "@/types/alerts"
import { NModal } from "naive-ui"
import { computed, defineAsyncComponent, inject, ref, toRefs } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import AlertDetailTabs from "./AlertDetailTabs.vue"
import AlertOverview from "./AlertOverview.vue"

const props = defineProps<{
	alert: Alert
	hideActions?: boolean
	hideOpen?: boolean
	embedded?: boolean
}>()

const AlertActions = defineAsyncComponent(() => import("./AlertActions.vue"))

const { alert, hideActions, hideOpen } = toRefs(props)

const { routeAlertsSiemAlert } = useNavigation()
const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

const socAlertCreationField = ref(inject<SocAlertField>("soc-alert-creation-field", "alert_url"))

const alertOpenUrl = computed(() => {
	if (!alert.value._index || !alert.value._id) return undefined
	return routeAlertsSiemAlert(alert.value._index, alert.value._id).fullUrl()
})
</script>
