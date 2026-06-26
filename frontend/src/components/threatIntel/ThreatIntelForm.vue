<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-3">
			<n-form-item label="IOC Value" :show-feedback="false">
				<n-input v-model:value.trim="iocValue" placeholder="IPv4, domain, or SHA256 hash" clearable />
			</n-form-item>
			<div class="flex justify-end">
				<n-button type="primary" :disabled="!isValid" @click="create()">Submit</n-button>
			</div>
			<div
				v-if="error || !!response"
				class="bg-secondary rounded-lg border"
				:class="error ? 'border-error' : 'border-success'"
			>
				<div v-if="error" class="px-4 py-2.5">
					{{ error }}
				</div>
				<div v-else class="divide-y divide-border">
					<div class="px-4 py-2.5">
						<div class="text-secondary mb-0.5 font-mono text-xs">type</div>
						<div>
							{{ response?.type || "-" }}
						</div>
					</div>
					<div class="px-4 py-2.5">
						<div class="text-secondary mb-0.5 font-mono text-xs">value</div>
						<div>
							{{ response?.value || "-" }}
						</div>
					</div>
					<div class="px-4 py-2.5">
						<div class="text-secondary mb-0.5 font-mono text-xs">ioc_source</div>
						<div>
							{{ response?.ioc_source || "-" }}
						</div>
					</div>
					<div class="px-4 py-2.5">
						<div class="text-secondary mb-0.5 font-mono text-xs">comment</div>
						<div>
							{{ response?.comment || "-" }}
						</div>
					</div>
					<div class="px-4 py-2.5">
						<div class="text-secondary mb-0.5 font-mono text-xs">score</div>
						<div>
							{{ response?.score || "-" }}
						</div>
					</div>
					<div class="px-4 py-2.5">
						<div class="text-secondary mb-0.5 font-mono text-xs">timestamp</div>
						<div>
							{{ response?.timestamp ? formatDate(response.timestamp, dFormats.datetime) : "-" }}
						</div>
					</div>
					<div class="px-4 py-2.5">
						<div class="text-secondary mb-0.5 font-mono text-xs">report_url</div>
						<div>
							<a v-if="response?.report_url" :href="response.report_url" target="_blank">
								{{ response.report_url }}
							</a>
							<span v-else>-</span>
						</div>
					</div>
					<div class="px-4 py-2.5">
						<div class="text-secondary mb-0.5 font-mono text-xs">virustotal_url</div>
						<div>
							<a v-if="response?.virustotal_url" :href="response.virustotal_url" target="_blank">
								{{ response.virustotal_url }}
							</a>
							<span v-else>-</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { ThreatIntelResponse } from "@/types/threat-intel"
import _trim from "lodash/trim"
import { NButton, NFormItem, NInput, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const iocValue = ref<string>("")
const response = ref<ThreatIntelResponse | null>(null)
const error = ref<string>("")
const isValid = computed(() => {
	return !!_trim(iocValue.value)
})

function clear() {
	iocValue.value = ""
}

function restore() {
	clear()
	loading.value = false
	response.value = null
	error.value = ""
}

function create() {
	loading.value = true

	Api.threatIntel
		.create(iocValue.value)
		.then(res => {
			if (res.data.success) {
				error.value = ""
				response.value = res.data.data
				clear()
				message.success(res.data?.message || "SOCFortress Threat Intel submitted.")
			} else {
				error.value = res.data?.message || "An error occurred. Please try again later."
				message.warning(error.value)
			}
		})
		.catch(err => {
			error.value = getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later."
			message.error(error.value)
		})
		.finally(() => {
			loading.value = false
		})
}

defineExpose({
	restore
})
</script>
