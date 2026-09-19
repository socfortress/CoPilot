<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-3">
			<n-form-item label="IOC Value" :show-feedback="false">
				<n-input-group>
					<n-input
						v-model:value.trim="iocValue"
						placeholder="IP, domain, URL, email or file hash"
						clearable
						@keydown.enter="isValid && lookup()"
					/>
					<n-button type="primary" :disabled="!isValid" @click="lookup()">Lookup</n-button>
				</n-input-group>
			</n-form-item>
			<div v-if="error" class="bg-secondary border-error rounded-lg border px-4 py-2.5">
				{{ error }}
			</div>
			<OpenCTILookupResult v-else-if="response" :lookup="response" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { OpenCTIObservableLookup } from "@/types/opencti"
import _trim from "lodash/trim"
import { NButton, NFormItem, NInput, NInputGroup, NSpin } from "naive-ui"
import { computed, ref } from "vue"
import { getApiErrorMessage } from "@/utils"
// TEMP(mock): UI/UX review — restore `import Api from "@/api"` and `Api.opencti` before merging.
import mockOpenCTI from "./__mock__/opencti-mock"
import OpenCTILookupResult from "./OpenCTILookupResult.vue"

const loading = ref(false)
const iocValue = ref<string>("")
const response = ref<OpenCTIObservableLookup | null>(null)
const error = ref<string>("")
const isValid = computed(() => !!_trim(iocValue.value))

function restore() {
	iocValue.value = ""
	loading.value = false
	response.value = null
	error.value = ""
}

function lookup() {
	loading.value = true
	error.value = ""

	mockOpenCTI
		.lookupObservable(_trim(iocValue.value))
		.then(res => {
			response.value = res.data
		})
		.catch(err => {
			response.value = null
			error.value = getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later."
		})
		.finally(() => {
			loading.value = false
		})
}

defineExpose({
	restore
})
</script>
