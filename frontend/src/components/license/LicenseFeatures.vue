<template>
	<div class="license-features" :class="{ loading }">
		<div class="license-features-box flex items-center justify-center">
			<n-spin :show="loading" class="h-full w-full" content-class="h-full">
				<div class="wrapper h-full flex flex-col gap-4" v-if="!loading">
					<h3>
						{{ features.length ? "Your features" : "Unlock features" }}
					</h3>
					<div class="grow overflow-hidden">
						<n-scrollbar v-if="!loading">
							<div class="features-list flex flex-col gap-2" v-if="license">
								<template v-if="activeSubscriptions.length">
									<SubscriptionCard
										v-for="subscription of activeSubscriptions"
										:key="subscription.id"
										:subscription="subscription"
										embedded
									/>
								</template>
								<n-empty description="No features unlocked" class="justify-center h-48" v-else>
									<template #icon>
										<Icon :name="NoFeaturesIcon"></Icon>
									</template>
								</n-empty>
							</div>
							<LicenseCheckoutWizard
								v-else
								:features-data="features"
								:subscriptions-data="subscriptions"
							/>
						</n-scrollbar>
					</div>
					<div class="cta-section" v-if="license">
						<n-button type="primary" @click="openCheckout()" class="!w-full" size="large">
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
				<span class="cursor-pointer" @click="showLicenseDetails = true">
					Your license:
					<strong>{{ license }}</strong>
					<Icon :name="InfoIcon" :size="14" class="relative top-0.5 ml-1"></Icon>
				</span>
			</template>
			<template v-else>
				<span class="cursor-pointer">If you possess a license, you may load it by clicking here</span>
			</template>
		</div>

		<n-modal
			v-model:show="showCheckoutForm"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			title="Add feature"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<LicenseCheckoutWizard :features-data="features" :subscriptions-data="subscriptions" />
		</n-modal>

		<n-modal
			v-model:show="showLicenseDetails"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			title="License details"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<LicenseDetails :features-data="features" hide-features v-if="license" embedded />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NScrollbar, NSpin, NModal, NButton, NEmpty, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount, onMounted, ref, toRefs, computed } from "vue"
import { type LicenseFeatures, type LicenseKey, type SubscriptionFeature } from "@/types/license.d"
import SubscriptionCard from "./SubscriptionCard.vue"
import LicenseCheckoutWizard from "./LicenseCheckoutWizard.vue"
import LicenseDetails from "./LicenseDetails.vue"

const emit = defineEmits<{
	(e: "licenseLoaded", value: LicenseKey): void
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
const NoFeaturesIcon = "carbon:intent-request-uninstall"

const message = useMessage()
const showCheckoutForm = ref(false)
const showLicenseDetails = ref(false)
const loadingLicense = ref(false)
const loadingFeatures = ref(false)
const loadingSubscriptions = ref(false)

const license = ref<LicenseKey | null>(null)
const features = ref<LicenseFeatures[]>([])
const subscriptions = ref<SubscriptionFeature[]>([])

const loading = computed(() => loadingLicense.value || loadingFeatures.value || loadingSubscriptions.value)

const activeSubscriptions = computed<SubscriptionFeature[]>(() =>
	features.value.map(f => subscriptions.value.find(s => s.name === f) as SubscriptionFeature).filter(o => !!o)
)

function getLicense() {
	loadingLicense.value = true

	Api.license
		.getLicense()
		.then(res => {
			if (res.data.success) {
				//license.value = res.data?.license_key
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
				//features.value = res.data?.features
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
	getLicense()
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
	display: flex;
	flex-direction: column;
	overflow: hidden;

	&.loading {
		min-height: 300px;
		min-width: 300px;
	}

	.license-features-box {
		background-color: var(--bg-color);
		border-radius: var(--border-radius);
		padding: 14px 18px;
		flex-grow: 1;
		overflow: hidden;
	}
	.footer {
		width: 100%;
		text-align: center;
		font-size: 12px;

		.cursor-pointer {
			&:hover {
				color: var(--primary-color);
			}
		}
	}
}
</style>
