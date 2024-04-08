<template>
	<n-spin :show="loading" class="min-h-48">
		<n-empty :description="errorMessage" class="justify-center h-48" v-if="errorMessage">
			<template #icon><Icon :name="WarningIcon"></Icon></template>
		</n-empty>
		<template v-else>
			<div class="list flex flex-col gap-2" v-if="availableSubscriptions.length">
				<SubscriptionCard
					v-for="subscription of availableSubscriptions"
					:key="subscription.id"
					:subscription="subscription"
					selectable
					embedded
				/>
			</div>
		</template>
	</n-spin>
</template>

<script setup lang="ts">
import { NSpin, NEmpty, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount, ref, toRefs } from "vue"
import { computed } from "vue"
import SubscriptionCard from "./SubscriptionCard.vue"
import type { LicenseFeatures, SubscriptionFeature } from "@/types/license.d"

const props = defineProps<{
	featuresData?: LicenseFeatures[]
	subscriptionsData?: SubscriptionFeature[]
}>()
const { featuresData, subscriptionsData } = toRefs(props)

const WarningIcon = "carbon:warning-alt"

const message = useMessage()
const loadingFeatures = ref(false)
const loadingSubscriptions = ref(false)
const loading = computed(() => loadingFeatures.value || loadingSubscriptions.value)

const featuresLoaded = ref<LicenseFeatures[]>([])
const subscriptionsLoaded = ref<SubscriptionFeature[]>([])
const features = computed(() => featuresLoaded.value || featuresData?.value || [])
const subscriptions = computed(() => subscriptionsLoaded.value || subscriptionsData?.value || [])

const availableSubscriptions = computed<SubscriptionFeature[]>(() =>
	subscriptions.value.filter(o => features.value.includes(o.name))
)

const errorMessage = ref<string | null>(null)

function getLicenseFeatures() {
	loadingFeatures.value = true

	Api.license
		.getLicenseFeatures()
		.then(res => {
			if (res.data.success) {
				featuresLoaded.value = res.data?.features
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
				subscriptionsLoaded.value = res.data?.features || []
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
	if (!features.value.length) {
		getLicenseFeatures()
	}
	if (!subscriptions.value.length) {
		getSubscriptionFeatures()
	}
})
</script>
