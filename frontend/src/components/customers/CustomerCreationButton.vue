<template>
	<div>
		<LicenseFeatureCheck
			v-if="!skipLicenseCheck && (customersCount || 0) < 5"
			feature="MSSP 5"
			@response="isMSSP5Enabled = $event"
		/>
		<LicenseFeatureCheck
			v-if="!skipLicenseCheck && (customersCount || 0) < 10"
			feature="MSSP 10"
			@response="isMSSP10Enabled = $event"
		/>
		<LicenseFeatureCheck
			v-if="!skipLicenseCheck"
			feature="MSSP Unlimited"
			@response="isMSSPUnlimitedEnabled = $event"
		/>

		<LicenseFeatureCheck
			feature="MSSP 5"
			disabled
			feedback="tooltip"
			:force-show-feedback="!licenseEnabled && !licenseLoading"
		>
			<n-button
				:size="size || 'small'"
				type="primary"
				:loading="licenseLoading && !skipLicenseCheck"
				:disabled="!licenseEnabled || disabled"
				@click="showAddCustomer = true"
			>
				<template #icon>
					<Icon :name="AddUserIcon" :size="14"></Icon>
				</template>
				<div class="flex items-center gap-2">
					<span>Add Customer</span>
					<Icon v-if="!licenseEnabled && !licenseLoading" :name="LockIcon" :size="14" />
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
				<CustomerForm
					:reset-on-submit="true"
					@mounted="customerFormCTX = $event"
					@submitted="emit('submitted')"
				/>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import { NButton, NDrawer, NDrawerContent } from "naive-ui"
import { computed, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import LicenseFeatureCheck from "@/components/license/LicenseFeatureCheck.vue"
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
const isMSSP5Enabled = ref<null | boolean>(null)
const isMSSP10Enabled = ref<null | boolean>(null)
const isMSSPUnlimitedEnabled = ref<null | boolean>(null)
const licenseLoading = computed<boolean>(
	() => isMSSP5Enabled.value === null || isMSSP10Enabled.value === null || isMSSPUnlimitedEnabled.value === null
)
const skipLicenseCheck = computed<boolean>(() => !customersCount)
const licenseEnabled = computed<boolean>(() => {
	if (skipLicenseCheck.value) {
		return true
	}

	if (isMSSPUnlimitedEnabled.value) {
		return true
	}

	if (isMSSP10Enabled.value && customersCount !== undefined && customersCount < 10) {
		return true
	}

	if (isMSSP5Enabled.value && customersCount !== undefined && customersCount < 5) {
		return true
	}

	return false
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
	() => customersCount,
	() => {
		if (customersCount === undefined) {
			return
		}
		if (customersCount >= 5) {
			isMSSP5Enabled.value = true
		}
		if (customersCount >= 10) {
			isMSSP10Enabled.value = true
		}
	},
	{ immediate: true }
)
</script>
