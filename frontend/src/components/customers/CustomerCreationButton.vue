<template>
	<LicenseFeatureCheck
		:feature="licenseKey"
		:disabled="licenseDisabled"
		feedback="tooltip"
		@response="
			(() => {
				licenseChecked = true
				licenseResponse = $event
			})()
		"
	>
		<n-button
			:size="size || 'small'"
			type="primary"
			:loading="!licenseChecked && !licenseDisabled"
			:disabled="!licenseChecked || !licenseResponse || disabled"
			@click="showAddCustomer = true"
		>
			<template #icon>
				<Icon :name="AddUserIcon" :size="14"></Icon>
			</template>
			<div class="flex items-center gap-2">
				<span>Add Customer</span>
				<Icon v-if="!licenseResponse && licenseChecked" :name="LockIcon" :size="14" />
			</div>
		</n-button>
	</LicenseFeatureCheck>

	<n-drawer
		v-model:show="showAddCustomer"
		:width="500"
		style="max-width: 90vw"
		:trap-focus="false"
		display-directive="show"
	>
		<n-drawer-content title="Add Customer" closable :native-scrollbar="false">
			<CustomerForm :reset-on-submit="true" @mounted="customerFormCTX = $event" @submitted="emit('submitted')" />
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import type { LicenseFeatures } from "@/types/license.d"
import type { Size } from "naive-ui/es/button/src/interface"
import Icon from "@/components/common/Icon.vue"
import LicenseFeatureCheck from "@/components/license/LicenseFeatureCheck.vue"
import { NButton, NDrawer, NDrawerContent } from "naive-ui"
import { computed, ref, watch } from "vue"
import CustomerForm from "./CustomerForm.vue"

const { customersCount, disabled, size } = defineProps<{
	customersCount?: number
	disabled?: boolean
	size?: Size
}>()

const emit = defineEmits<{
	(e: "submitted"): void
}>()

const openForm = defineModel<boolean | undefined>("openForm", { default: false })

const LockIcon = "carbon:locked"
const AddUserIcon = "carbon:user-follow"
const customerFormCTX = ref<{ reset: () => void } | null>(null)
const showAddCustomer = ref(false)

const licenseChecked = ref(!customersCount)
const licenseResponse = ref(!customersCount)
const licenseDisabled = computed<boolean>(() => !customersCount)
const licenseKey = computed<LicenseFeatures>(() => {
	let key: LicenseFeatures = "MSSP 5"

	if (customersCount && customersCount >= 5) {
		key = "MSSP 10"
	}

	if (customersCount && customersCount >= 10) {
		key = "MSSP Unlimited"
	}

	return key
})

watch(showAddCustomer, val => {
	if (!val) {
		openForm.value = false
	}
	customerFormCTX.value?.reset()
})

watch(
	openForm,
	val => {
		if (val) {
			showAddCustomer.value = true
		}
	},
	{ immediate: true }
)

watch(
	licenseKey,
	() => {
		licenseResponse.value = !customersCount
		licenseChecked.value = !customersCount
	},
	{ immediate: true }
)
</script>
