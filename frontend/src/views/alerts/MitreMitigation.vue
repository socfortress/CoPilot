<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<n-spin :show="loading">
			<MitigationOverview v-if="mitigationDetails" :entity="mitigationDetails" full-width />
			<n-empty v-else-if="!loading" description="Mitigation not found" class="h-48 justify-center" />
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { MitreMitigationDetails } from "@/types/mitre"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import MitigationOverview from "@/components/mitre/Mitigation/MitigationOverview.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const route = useRoute()
const router = useRouter()
const { routeAlertsMitre } = useNavigation()
const message = useMessage()

const BackIcon = "carbon:arrow-left"

const loading = ref(false)
const mitigationDetails = ref<MitreMitigationDetails | undefined>(undefined)

const mitigationId = computed(() => {
	const raw = route.params.mitigationId
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

function getDetails(id: string) {
	loading.value = true

	Api.wazuh.mitre
		.getMitreMitigations({ id })
		.then(res => {
			if (res.data.success) {
				mitigationDetails.value = res.data.results?.[0]
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeAlertsMitre().navigate()
}

onBeforeMount(() => {
	if (mitigationId.value) {
		getDetails(mitigationId.value)
	}
})
</script>
