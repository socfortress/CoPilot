<template>
	<n-spin :show="loading" content-class="flex flex-col gap-4">
		<n-input v-model:value="licenseKey" placeholder="Insert your license" clearable />
		<div class="flex justify-end">
			<n-button type="success" :loading="loadingReplace" :disabled="!licenseKey" @click="replaceLicense()">
				<template #icon>
					<Icon :name="LicenseIcon"></Icon>
				</template>
				Load License
			</n-button>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { NInput, NButton, NSpin, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { ref } from "vue"
import { computed } from "vue"
import type { LicenseKey } from "@/types/license.d"

const emit = defineEmits<{
	(e: "uploaded"): void
}>()

const LicenseIcon = "carbon:license"

const message = useMessage()
const loadingReplace = ref(false)
const licenseKey = ref<LicenseKey | "">("")
const loading = computed(() => loadingReplace.value)

function replaceLicense() {
	if (!licenseKey.value) {
		return
	}

	loadingReplace.value = true

	Api.license
		.replaceLicense(licenseKey.value)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "License replaced successfully")
				emit("uploaded")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingReplace.value = false
		})
}
</script>
