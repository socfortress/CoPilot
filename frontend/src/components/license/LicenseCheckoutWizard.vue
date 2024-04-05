<template>
	<n-spin :show="loading" class="min-h-48">
		<n-empty :description="errorMessage" class="justify-center h-48" v-if="errorMessage">
			<template #icon><Icon :name="WarningIcon"></Icon></template>
		</n-empty>
		<template v-else>
			<div class="list flex flex-col gap-2" v-if="subscriptions.length">
				<div class="list-title">Available features:</div>
				<SubscriptionCard
					v-for="subscription of subscriptions"
					:key="subscription.id"
					:subscription="subscription"
					embedded
				/>
			</div>
			<div class="list flex flex-col gap-2" v-if="subscriptions.length">
				<div class="list-title">Current features:</div>
				<SubscriptionCard
					v-for="subscription of subscriptions"
					:key="subscription.id"
					:subscription="subscription"
					embedded
				/>
			</div>
		</template>
	</n-spin>
</template>

<script setup lang="ts">
import { NButton, NSpin, NEmpty, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount, ref, watch } from "vue"
import { computed } from "vue"
import SubscriptionCard from "./SubscriptionCard.vue"
import type { LicenseFeatures, LicenseKey, SubscriptionFeature } from "@/types/license.d"

const LoadingIcon = "eos-icons:loading"
const LicenseIcon = "carbon:license"
const ExtendIcon = "carbon:intent-request-create"
const WarningIcon = "carbon:warning-alt"

const message = useMessage()
const loadingFeatures = ref(false)
const loadingSubscriptions = ref(false)
const loading = computed(() => loadingFeatures.value || loadingSubscriptions.value)

const subscriptions = ref<SubscriptionFeature[]>([])
const features = ref<LicenseFeatures[]>([])
const errorMessage = ref<string | null>(null)

function getLicenseFeatures() {
	loadingFeatures.value = true

	Api.license
		.getLicenseFeatures()
		.then(res => {
			if (res.data.success) {
				features.value = res.data?.features
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response.status !== 404) {
				errorMessage.value = "We're sorry, there was an issue loading your license"
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingFeatures.value = false
		})
}

function getSubscriptionFeatures() {
	loadingSubscriptions.value = true

	Api.license
		.getSubscriptionFeatures()
		.then(res => {
			if (res.data.success) {
				subscriptions.value = res.data?.features || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingSubscriptions.value = false
		})
}

onBeforeMount(() => {
	getLicenseFeatures()
	getSubscriptionFeatures()
})
</script>
