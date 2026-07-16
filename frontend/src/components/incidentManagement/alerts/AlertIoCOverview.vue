<template>
	<n-spin
		:show="loading"
		:class="fullWidth ? 'py-4' : 'p-6'"
		content-class="flex flex-col gap-4"
		class="min-h-40"
		:size="18"
	>
		<template v-if="resolvedIoc">
			<div class="flex flex-wrap items-center gap-3">
				<VirusTotalEnrichmentButton :ioc-value="resolvedIoc.value" />
			</div>

			<div class="grid-auto-fit-200 grid gap-2">
				<CardKV v-for="(value, key) of resolvedIoc" :key>
					<template #key>
						{{ key }}
					</template>
					<template #value>
						{{ value === "" ? "-" : (value ?? "-") }}
					</template>
				</CardKV>
			</div>
		</template>

		<n-empty v-else-if="!loading" description="IoC not found" class="h-32 justify-center" />
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertIOC } from "@/types/incidentManagement/alerts"
import { NEmpty, NSpin } from "naive-ui"
import { defineAsyncComponent } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"

const {
	ioc,
	alertId,
	iocId,
	fullWidth = false
} = defineProps<{
	ioc?: AlertIOC
	alertId?: number
	iocId?: number
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: AlertIOC): void
}>()

const VirusTotalEnrichmentButton = defineAsyncComponent(
	() => import("@/components/threatIntel/VirusTotalEnrichmentButton.vue")
)

// no by-id endpoint for a single IoC: we fetch the whole alert and pick the IoC client-side
const { loading, entity: resolvedIoc } = useEntityDetails<AlertIOC, string>({
	entity: () => ioc,
	id: () => (alertId != null && iocId != null ? `${alertId}|${iocId}` : null),
	// the endpoint takes no abort signal, so the request itself is not cancellable
	fetch: () =>
		Api.incidentManagement.alerts.getAlert(alertId as number).then(res => {
			if (!res.data.success) {
				return { entity: null, message: res.data?.message || "An error occurred. Please try again later." }
			}

			return { entity: res.data.alerts?.[0]?.iocs?.find(item => item.id === iocId) ?? null }
		}),
	notFoundMessage: "IoC not found",
	errorMessage: "An error occurred. Please try again later.",
	onLoaded: value => emit("loaded", value)
})
</script>
