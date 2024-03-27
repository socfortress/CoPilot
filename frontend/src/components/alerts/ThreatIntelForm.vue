<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-3">
			<div class="flex flex-col gap-1">
				<small class="ml-2">IOC Value:</small>
				<n-input v-model:value.trim="iocValue" placeholder="IPv4, domain, or SHA256 hash" clearable />
			</div>
			<div class="flex justify-end">
				<n-button type="primary" :disabled="!isValid" @click="create()">Submit</n-button>
			</div>
			<div class="response" :class="{ error }" v-if="error || !!response">
				<div class="message" v-if="error">
					{{ error }}
				</div>
				<div v-else class="list">
					<div class="item">
						<div class="key">type</div>
						<div class="value">{{ response?.type || "-" }}</div>
					</div>
					<div class="item">
						<div class="key">value</div>
						<div class="value">{{ response?.value || "-" }}</div>
					</div>
					<div class="item">
						<div class="key">ioc_source</div>
						<div class="value">{{ response?.ioc_source || "-" }}</div>
					</div>
					<div class="item">
						<div class="key">comment</div>
						<div class="value">{{ response?.comment || "-" }}</div>
					</div>
					<div class="item">
						<div class="key">score</div>
						<div class="value">{{ response?.score || "-" }}</div>
					</div>
					<div class="item">
						<div class="key">timestamp</div>
						<div class="value">
							{{ response?.timestamp ? formatDate(response.timestamp, dFormats.datetime) : "-" }}
						</div>
					</div>
					<div class="item">
						<div class="key">report_url</div>
						<div class="value">
							<a :href="response.report_url" target="_blank" v-if="response?.report_url">
								{{ response.report_url }}
							</a>
							<span v-else>-</span>
						</div>
					</div>
					<div class="item">
						<div class="key">virustotal_url</div>
						<div class="value">
							<a :href="response.virustotal_url" target="_blank" v-if="response?.virustotal_url">
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
import { ref, computed, onMounted } from "vue"
import { useMessage, NSpin, NButton, NInput } from "naive-ui"
import Api from "@/api"
import _trim from "lodash/trim"
import type { ThreatIntelResponse } from "@/types/threatIntel.d"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const emit = defineEmits<{
	(
		e: "mounted",
		value: {
			restore: () => void
		}
	): void
}>()

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
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			error.value = err.response?.data?.message || "An error occurred. Please try again later."
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onMounted(() => {
	emit("mounted", {
		restore
	})
})
</script>

<style scoped lang="scss">
.response {
	background-color: var(--bg-secondary-color);
	border-radius: var(--border-radius);
	border: 1px solid var(--success-color);

	.message {
		padding: 10px 16px;
	}

	.list {
		.item {
			padding: 10px 16px;

			.key {
				color: var(--fg-secondary-color);
				font-size: 12px;
				margin-bottom: 2px;
				font-family: var(--font-family-mono);
			}

			&:not(:last-child) {
				border-bottom: var(--border-small-100);
			}
		}
	}

	&.error {
		border-color: var(--error-color);
	}
}
</style>
