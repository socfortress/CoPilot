<template>
	<div v-if="alert.iocs?.length" class="flex flex-col gap-2" data-testid="alert-iocs">
		<n-alert v-if="loadError" type="warning" :bordered="false" data-testid="ioc-ti-load-error">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<span>{{ loadError }}</span>
				<n-button size="small" secondary @click="load()">{{ $t("common.actions.tryAgain") }}</n-button>
			</div>
		</n-alert>

		<CardEntity
			v-for="ioc in alert.iocs"
			:key="ioc.id"
			size="small"
			embedded
			:loading="loading && !enrichment[ioc.id]"
			data-testid="alert-ioc"
			:data-ioc="ioc.id"
		>
			<template #header-main>
				<bdi class="break-all">{{ ioc.ioc_value || ioc.value }}</bdi>
			</template>
			<template #header-extra>
				<bdi>{{ ioc.ioc_type || ioc.type }}</bdi>
			</template>
			<template #default>
				<div class="flex flex-col gap-2">
					<span v-if="ioc.ioc_description || ioc.description">{{ ioc.ioc_description || ioc.description }}</span>
					<IocThreatIntel v-if="enrichment[ioc.id]" :alert-id="alert.id" :ioc="enrichment[ioc.id]!" @updated="update" />
				</div>
			</template>
		</CardEntity>
	</div>

	<n-empty v-else :description="$t('alerts.iocs.empty')" class="min-h-50 justify-center" />
</template>

<script setup lang="ts">
import type { Alert } from "@/types/alerts"
import type { IocEnrichment } from "@/types/iocEnrichment"
import { NAlert, NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useIocEnrichmentAvailability } from "@/composables/common/useIocEnrichmentAvailability"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { byIocId } from "./iocEnrichment"
import IocThreatIntel from "./IocThreatIntel.vue"

/**
 * The alert's IOCs, each with what the SOC's Threat Intel says about it when the customer has that
 * switched on (#1318). Opening them reads only what the SOC keeps; a source is asked when the user
 * checks one IOC.
 */

const { alert } = defineProps<{
	alert: Alert
}>()

const { t } = useI18n()
const { isEnabledFor } = useIocEnrichmentAvailability()
const { loading, run } = useLatestRequest()

const enrichment = ref<Record<number, IocEnrichment>>({})
const loadError = ref<string | null>(null)

async function load() {
	loadError.value = null
	if (!alert.iocs?.length || !(await isEnabledFor(alert.customer_code))) {
		enrichment.value = {}
		return
	}
	await run(
		async signal => {
			const res = await Api.iocEnrichment.getForAlert(alert.id, signal)
			enrichment.value = byIocId(res.data.iocs ?? [])
		},
		() => {
			// The server's text is not the user's concern here: the retry is.
			loadError.value = t("iocEnrichment.loadFailed")
		}
	)
}

function update(ioc: IocEnrichment) {
	enrichment.value = { ...enrichment.value, [ioc.ioc_id]: ioc }
}

watch(
	() => [alert.id, alert.customer_code] as const,
	() => {
		enrichment.value = {}
		load()
	},
	{ immediate: true }
)
</script>
