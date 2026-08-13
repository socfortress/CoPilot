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
import { NSpin } from "naive-ui"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useSettingsStore } from "@/stores/settings"
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

const dFormats = useSettingsStore().dateFormat

const { loading, entity: resolvedIoc } = useEntityDetails<AiAnalystIoc, number>({
	entity: () => props.ioc,
	id: () => props.iocId,
	fetch: (id, signal) =>
		Api.aiAnalyst.getIoc(id, signal).then(res => ({
			entity: res.data.success ? (res.data.ioc ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "IOC not found.",
	errorMessage: "Failed to load IOC.",
	onLoaded: value => emit("loaded", value)
})

function verdictColor(verdict: string) {
	if (verdict === "malicious") return "danger"
	if (verdict === "suspicious") return "warning"
	if (verdict === "clean") return "success"
	return undefined
}

defineExpose({ loading, resolvedIoc })
</script>
