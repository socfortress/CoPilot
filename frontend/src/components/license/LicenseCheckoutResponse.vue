<template>
	<n-card
		class="license-checkout-response"
		size="large"
		:class="type"
		content-class="flex flex-col items-center gap-5"
	>
		<template v-if="type === 'success'">
			<Icon :name="CheckIcon" class="text-success-color" :size="100" />
			<h1 class="text-center">Congratulations!</h1>
			<p class="text-center">Your checkout was successful, and your license will be updated soon.</p>
			<n-spin v-if="loadingLicense" :size="24" />
			<h4 v-if="license">
				{{ license }}
			</h4>
		</template>
		<template v-if="type === 'error'">
			<Icon :name="ErrorIcon" class="text-error-color" :size="100"></Icon>
			<h1 class="text-center">Checkout canceled</h1>
		</template>
		<div>
			<n-button @click="gotoLicense()">
				<template #icon>
					<Icon :name="LicenseIcon"></Icon>
				</template>
				View license
			</n-button>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import { NButton, NCard, NSpin, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import type { LicenseKey } from "@/types/license"
import { useGoto } from "@/composables/useGoto"

const props = defineProps<{ type: "success" | "error"; data?: { email?: string } }>()
const { type, data } = toRefs(props)

const ErrorIcon = "majesticons:exclamation-line"
const LicenseIcon = "carbon:license"
const CheckIcon = "carbon:checkmark-outline"
const { gotoLicense } = useGoto()
const message = useMessage()
const loadingLicense = ref(false)
const license = ref<LicenseKey | null>(null)

function getLicense(email: string) {
	loadingLicense.value = true

	Api.license
		.retrieveLicenseByEmail(email)
		.then(res => {
			if (res.data.success) {
				license.value = res.data?.license_key
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

onBeforeMount(() => {
	if (data.value?.email) {
		getLicense(data.value.email)
	}
})
</script>
