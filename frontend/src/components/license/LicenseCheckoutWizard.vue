<template>
	<n-spin :show="loading" class="min-h-48">
		<n-empty :description="errorMessage" class="justify-center h-48" v-if="errorMessage">
			<template #icon><Icon :name="WarningIcon"></Icon></template>
		</n-empty>
		<template v-else>
			<template v-if="!selectedSubscription">
				<div class="list flex flex-col gap-2" v-if="availableSubscriptions.length">
					<SubscriptionCard
						v-for="subscription of availableSubscriptions"
						:key="subscription.id"
						:subscription="subscription"
						selectable
						embedded
						class="item-appear item-appear-bottom item-appear-005"
						@click="selectedSubscription = subscription"
					/>
				</div>
				<template v-else>
					<n-empty
						description="Congratulations, you have already unlocked all available features"
						class="justify-center h-48"
						v-if="!loading"
					>
						<template #icon>
							<Icon :name="CheckIcon"></Icon>
						</template>
					</n-empty>
				</template>
			</template>
			<template v-else>
				<SubscriptionCard :subscription="selectedSubscription" embedded hide-details />
				<div class="checkout-form item-appear item-appear-bottom item-appear-005 mt-8">
					<n-spin :show="loadingLicense || loadingSession">
						<n-form :label-width="80" :model="checkoutForm" :rules="rules" ref="formRef">
							<div class="flex flex-col gap-1">
								<n-form-item label="Company Name" path="company_name">
									<n-input
										v-model:value.trim="checkoutForm.company_name"
										placeholder="Input Company Name..."
										clearable
									/>
								</n-form-item>
								<n-form-item label="Email" path="customer_email">
									<n-input
										v-model:value.trim="checkoutForm.customer_email"
										placeholder="Input email..."
										clearable
									/>
								</n-form-item>
								<div class="flex justify-end gap-4">
									<n-button quaternary @click="selectedSubscription = null">
										<template #icon>
											<Icon :name="ArrowLeftIcon"></Icon>
										</template>
										Back
									</n-button>
									<n-button
										type="success"
										:disabled="!isValid"
										@click="createCheckoutSession()"
										:loading="loadingSession"
									>
										<template #icon>
											<Icon :name="CartIcon"></Icon>
										</template>
										Checkout
									</n-button>
								</div>
							</div>
						</n-form>
					</n-spin>
				</div>
			</template>
		</template>
	</n-spin>
</template>

<script setup lang="ts">
import {
	NSpin,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NButton,
	useMessage,
	type FormItemRule,
	type FormRules
} from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount, ref, toRefs } from "vue"
import { computed } from "vue"
import SubscriptionCard from "./SubscriptionCard.vue"
import type { CheckoutPayload, License, LicenseCustomer, LicenseFeatures, SubscriptionFeature } from "@/types/license.d"
import isEmail from "validator/es/lib/isEmail"
import { watch } from "vue"

const props = defineProps<{
	featuresData?: LicenseFeatures[]
	subscriptionsData?: SubscriptionFeature[]
}>()
const { featuresData, subscriptionsData } = toRefs(props)

const WarningIcon = "carbon:warning-alt"
const CartIcon = "carbon:shopping-cart"
const CheckIcon = "carbon:checkmark-outline"
const ArrowLeftIcon = "carbon:arrow-left"

const message = useMessage()
const loadingFeatures = ref(false)
const loadingSubscriptions = ref(false)
const loadingLicense = ref(false)
const loadingSession = ref(false)
const loading = computed(() => loadingFeatures.value || loadingSubscriptions.value)
const selectedSubscription = ref<SubscriptionFeature | null>(null)
const errorMessage = ref<string | null>(null)
const checkoutForm = ref<CheckoutPayload>(getCheckoutForm())

const license = ref<License | null>(null)
const featuresLoaded = ref<LicenseFeatures[]>([])
const subscriptionsLoaded = ref<SubscriptionFeature[]>([])
const features = computed(() => featuresLoaded.value || featuresData?.value || [])
const subscriptions = computed(() => subscriptionsLoaded.value || subscriptionsData?.value || [])
const availableSubscriptions = computed<SubscriptionFeature[]>(() =>
	subscriptions.value.filter(o => !features.value.includes(o.name))
)
const isValid = computed(() => {
	if (!checkoutForm.value.company_name) {
		return false
	}

	if (!isEmail(checkoutForm.value.customer_email)) {
		return false
	}

	return true
})

const rules: FormRules = {
	company_name: {
		required: true,
		message: "Please input company name",
		trigger: ["input", "blur"]
	},
	customer_email: {
		required: true,
		trigger: ["input", "blur"],
		validator: (rule: FormItemRule, value: string) => {
			if (!value) {
				return new Error("Email is required")
			}
			if (!isEmail(value)) {
				return new Error("The email is not formatted correctly")
			}
		}
	}
}

watch(selectedSubscription, val => {
	if (val && !license.value) {
		getLicense()
	}
})

function getCheckoutForm(args?: {
	email?: string
	companyName?: string
	customer?: LicenseCustomer
	subscription?: SubscriptionFeature | null
}): CheckoutPayload {
	const customerEmail = args?.email || args?.customer?.email || ""
	const companyName = args?.companyName || args?.customer?.companyName || ""

	return {
		feature_id: args?.subscription?.id || 0,
		cancel_url: `${location.origin}/license/cancel`,
		success_url: `${location.origin}/license/success?email=${customerEmail}`,
		customer_email: customerEmail,
		company_name: companyName
	}
}

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

function getLicense() {
	loadingLicense.value = true

	Api.license
		.verifyLicense()
		.then(res => {
			if (res.data.success) {
				license.value = res.data?.license
				checkoutForm.value = getCheckoutForm({ customer: license.value.customer })
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

function createCheckoutSession() {
	loadingSession.value = true

	const payload = getCheckoutForm({
		email: checkoutForm.value.customer_email,
		companyName: checkoutForm.value.company_name,
		subscription: selectedSubscription.value
	})

	Api.license
		.createCheckoutSession(payload)
		.then(res => {
			if (res.data.success) {
				window.location.href = res.data.session.url
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
			loadingSession.value = false
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
