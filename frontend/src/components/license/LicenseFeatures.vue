<template>
	<div class="license-features">
		<div class="license-features-box flex items-center justify-center">
			<n-spin :show="loading" class="h-full" content-class="h-full">
				<div class="wrapper h-full flex flex-col" v-if="!loading">
					<h3>
						{{ features.length ? "Your features" : "Add features to unlock power" }}
					</h3>
					<div class="features-list grow">
						<template v-if="activeSubscriptions.length">
							<SubscriptionCard
								v-for="subscription of activeSubscriptions"
								:key="subscription.id"
								:subscription="subscription"
								embedded
							/>
						</template>
						<LicenseCheckoutWizard v-else />
					</div>
					<div class="cta-section" v-if="activeSubscriptions.length">
						<n-button type="primary" @click="openCheckout()">
							<template #icon>
								<Icon :name="ExtendIcon"></Icon>
							</template>
							Add feature
						</n-button>
					</div>
				</div>
			</n-spin>
		</div>

		<div class="footer mt-3" v-if="!hideKey && !loading">
			<template v-if="license">
				Your license:
				<strong>{{ license.key }}</strong>
				<Icon :name="InfoIcon" :size="14" class="relative top-0.5 ml-1"></Icon>
			</template>
		</div>

		<n-modal
			v-model:show="showCheckoutForm"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			title="Add feature "
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<LicenseCheckoutWizard />
		</n-modal>

		<n-modal
			v-model:show="showLicenseDetails"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			title="Add feature "
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<LicenseDetails />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
// TODO: features-list: add scroller
import { NSpin, NModal, NButton, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount, onMounted, ref, toRefs } from "vue"
import { computed } from "vue"
import { LicenseFeatures, type License, type SubscriptionFeature } from "@/types/license.d"
import SubscriptionCard from "./SubscriptionCard.vue"
import LicenseCheckoutWizard from "./LicenseCheckoutWizard.vue"

const emit = defineEmits<{
	(e: "licenseLoaded", value: License): void
	(
		e: "mounted",
		value: {
			reload: () => void
		}
	): void
}>()

const props = defineProps<{ hideKey?: boolean }>()
const { hideKey } = toRefs(props)

const InfoIcon = "carbon:information"
const ExtendIcon = "carbon:intent-request-create"

const message = useMessage()
const showCheckoutForm = ref(false)
const showLicenseDetails = ref(false)
const loadingLicense = ref(false)
const loadingFeatures = ref(false)
const loadingSubscriptions = ref(false)

const license = ref<License | null>(null)
const features = ref<LicenseFeatures[]>([])
const subscriptions = ref<SubscriptionFeature[]>([])

const loading = computed(() => loadingLicense.value || loadingFeatures.value || loadingSubscriptions.value)

const activeSubscriptions = computed<SubscriptionFeature[]>(() =>
	features.value.map(f => subscriptions.value.find(s => s.name === f) as SubscriptionFeature).filter(o => !!o)
)

function getLicense() {
	loadingLicense.value = true

	Api.license
		.verifyLicense()
		.then(res => {
			if (res.data.success) {
				license.value = res.data?.license
				//emit("licenseLoaded", license.value)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response.status !== 404) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingLicense.value = false
		})
}

function getLicenseFeatures() {
	loadingFeatures.value = true

	Api.license
		.getLicenseFeatures()
		.then(res => {
			if (res.data.success) {
				features.value = res.data?.features
				if (features.value.length) {
					getSubscriptionFeatures()
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response.status !== 404) {
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

function openCheckout() {
	showCheckoutForm.value = true
}

function load() {
	if (!hideKey.value) {
		getLicense()
	}
	getLicenseFeatures()
}

onBeforeMount(() => {
	load()
})

onMounted(() => {
	emit("mounted", {
		reload: load
	})
})
</script>

<style lang="scss" scoped>
.license-features {
	min-height: 300px;
	min-width: 300px;
	display: flex;
	flex-direction: column;
	.license-features-box {
		background-color: var(--bg-color);
		border-radius: var(--border-radius);
		padding: 14px 18px;
		flex-grow: 1;
	}
	.footer {
		width: 100%;
		text-align: center;
		font-size: 12px;
	}
}
</style>
