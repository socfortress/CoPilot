<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-2">
			<template v-if="iocs.length">
				<n-card v-for="ioc of iocs" :key="ioc.id" size="small" embedded>
					<div class="flex flex-wrap items-center gap-3">
						<Badge type="splitted" bright>
							<template #label>Type</template>
							<template #value>{{ ioc.ioc_type }}</template>
						</Badge>
						<Badge type="splitted" bright :color="verdictColor(ioc.vt_verdict)">
							<template #label>VT Verdict</template>
							<template #value>{{ ioc.vt_verdict }}</template>
						</Badge>
						<Badge v-if="ioc.vt_score" type="splitted">
							<template #label>VT Score</template>
							<template #value>{{ ioc.vt_score }}</template>
						</Badge>
					</div>
					<div class="mt-2">
						<code class="text-sm break-all">{{ ioc.ioc_value }}</code>
					</div>
					<div v-if="ioc.details" class="mt-2 text-sm opacity-70">
						{{ ioc.details }}
					</div>
				</n-card>
			</template>
			<n-empty v-else-if="!loading" description="No IOCs found for this alert" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystIoc } from "@/types/aiAnalyst.d"
import { NCard, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"

const props = defineProps<{
	alertId: number
}>()

const { alertId } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const iocs = ref<AiAnalystIoc[]>([])

function verdictColor(verdict: string) {
	if (verdict === "malicious") return "danger"
	if (verdict === "suspicious") return "warning"
	if (verdict === "clean") return "success"
	return undefined
}

function getData() {
	loading.value = true

	Api.aiAnalyst
		.getIocsByAlert(alertId.value)
		.then(res => {
			if (res.data.success) {
				iocs.value = res.data?.iocs || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
