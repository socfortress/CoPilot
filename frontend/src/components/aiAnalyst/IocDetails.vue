<template>
	<n-spin :show="loading">
		<CardEntity v-if="resolvedIoc" size="small" :embedded>
			<template #default>
				<CodeSource :code="resolvedIoc.ioc_value" />
			</template>
			<template v-if="resolvedIoc.details" #mainExtra>
				{{ resolvedIoc.details }}
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" bright size="small">
						<template #label>Type</template>
						<template #value>{{ resolvedIoc.ioc_type }}</template>
					</Badge>
					<Badge type="splitted" bright :color="verdictColor(resolvedIoc.vt_verdict)" size="small">
						<template #label>VT Verdict</template>
						<template #value>{{ resolvedIoc.vt_verdict }}</template>
					</Badge>
					<Badge v-if="resolvedIoc.vt_score" type="splitted" size="small">
						<template #label>VT Score</template>
						<template #value>{{ resolvedIoc.vt_score }}</template>
					</Badge>
					<template v-if="!embedded">
						<Badge type="splitted" size="small">
							<template #label>Alert</template>
							<template #value>#{{ resolvedIoc.alert_id }}</template>
						</Badge>
						<Badge type="splitted" size="small">
							<template #label>Report</template>
							<template #value>#{{ resolvedIoc.report_id }}</template>
						</Badge>
						<Badge type="splitted" size="small">
							<template #label>Customer</template>
							<template #value>{{ resolvedIoc.customer_code }}</template>
						</Badge>
						<Badge type="splitted" size="small">
							<template #label>Created</template>
							<template #value>
								{{ formatDate(resolvedIoc.created_at, dFormats.datetime, { tz: true }) }}
							</template>
						</Badge>
					</template>
				</div>
			</template>
			<template v-if="$slots.footerExtra" #footerExtra>
				<slot name="footerExtra" />
			</template>
		</CardEntity>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystIoc } from "@/types/ai-analyst"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = withDefaults(
	defineProps<{
		ioc?: AiAnalystIoc | null
		iocId?: number | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: AiAnalystIoc): void
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const fetchedIoc = ref<AiAnalystIoc | null>(null)

let abortController: AbortController | null = null

const resolvedIoc = computed(() => props.ioc ?? fetchedIoc.value)

function verdictColor(verdict: string) {
	if (verdict === "malicious") return "danger"
	if (verdict === "suspicious") return "warning"
	if (verdict === "clean") return "success"
	return undefined
}

function loadIoc(iocId: number) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.aiAnalyst
		.getIoc(iocId, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.ioc) {
				fetchedIoc.value = res.data.ioc
				emit("loaded", res.data.ioc)
			} else {
				message.warning(res.data?.message || "IOC not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load IOC.")
				loading.value = false
			}
		})
}

watch(
	() => [props.ioc, props.iocId] as const,
	([ioc, iocId]) => {
		if (ioc) {
			abortController?.abort()
			fetchedIoc.value = null
			loading.value = false
			return
		}

		if (iocId != null) {
			loadIoc(iocId)
			return
		}

		abortController?.abort()
		fetchedIoc.value = null
		loading.value = false
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedIoc })
</script>
