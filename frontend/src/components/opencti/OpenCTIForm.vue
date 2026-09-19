<template>
	<!--
		With a result on screen the whole block dims so stale content isn't read as
		fresh; with nothing to protect, only the button shows the wait.
	-->
	<n-spin :show="loading && hasResult">
		<div class="flex flex-col gap-3">
			<n-form-item label="IOC Value" :show-feedback="false">
				<n-input-group>
					<n-input
						v-model:value.trim="iocValue"
						placeholder="IP, domain, URL, email or file hash"
						clearable
						:disabled="loading"
						@keydown.enter="isValid && lookup()"
					/>
					<n-button type="primary" :disabled="!isValid" :loading="loading && !hasResult" @click="lookup()">
						Lookup
					</n-button>
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
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import OpenCTILookupResult from "./OpenCTILookupResult.vue"

const loading = ref(false)
const iocValue = ref<string>("")
const response = ref<OpenCTIObservableLookup | null>(null)
const error = ref<string>("")
const isValid = computed(() => !!_trim(iocValue.value))
const hasResult = computed(() => !!response.value || !!error.value)

function restore() {
	iocValue.value = ""
	loading.value = false
	response.value = null
	error.value = ""
}

function lookup() {
	loading.value = true

	Api.opencti
		.lookupObservable(_trim(iocValue.value))
		.then(res => {
			error.value = ""
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
