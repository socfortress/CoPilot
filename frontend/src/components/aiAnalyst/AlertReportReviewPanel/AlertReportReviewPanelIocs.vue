<template>
	<n-card title="IOC verdict corrections" size="small" segmented>
		<n-spin :show="loading" class="min-h-40">
			<div class="flex flex-col gap-3">
				<p class="text-sm">
					Toggle off any IOC where the VirusTotal verdict above was wrong. Optionally note why.
				</p>
				<div v-if="iocs.length" class="flex flex-col gap-2">
					<CardEntity v-for="ioc of iocs" :key="ioc.id" size="small" embedded>
						<template #headerExtra>
							<div class="flex items-center gap-3">
								<Badge type="splitted" bright>
									<template #label>Type</template>
									<template #value>{{ ioc.ioc_type }}</template>
								</Badge>
								<Badge type="splitted" bright :color="verdictColor(ioc.vt_verdict)">
									<template #label>VT</template>
									<template #value>{{ ioc.vt_verdict }}</template>
								</Badge>
								<n-tooltip placement="top">
									<template #trigger>
										<n-switch
											:value="iocCorrect(ioc.id)"
											@update:value="setIocCorrect(ioc.id, $event)"
										/>
									</template>
									{{ iocCorrect(ioc.id) ? "Verdict correct" : "Verdict wrong" }}
								</n-tooltip>
							</div>
						</template>
						<template #default>
							<CodeSource :code="ioc.ioc_value" />
						</template>
						<template #mainExtra>
							<n-input
								:value="iocNote(ioc.id)"
								type="textarea"
								placeholder="Optional reviewer note"
								:autosize="{ minRows: 1, maxRows: 4 }"
								@update:value="setIocNote(ioc.id, $event)"
							/>
						</template>
					</CardEntity>
				</div>
				<n-empty v-else description="No IOCs recorded for this report" class="min-h-24 justify-center" />
			</div>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import type { AiAnalystIoc, AiAnalystReport } from "@/types/aiAnalyst.d"
import { NCard, NEmpty, NInput, NSpin, NSwitch, NTooltip, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CodeSource from "@/components/common/CodeSource.vue"

export interface IocState {
	verdict_correct: boolean
	note: string
}

const props = defineProps<{
	report: AiAnalystReport
}>()

const { report } = toRefs(props)

// Per-IOC review state — keyed by ioc.id so order stays stable with the list
const iocState = defineModel<Map<number, IocState>>("state", { required: true, default: () => new Map() })
const iocs = defineModel<AiAnalystIoc[]>("iocs", { required: true, default: () => [] })

const message = useMessage()
const loading = ref(false)

function iocCorrect(iocId: number): boolean {
	return iocState.value.get(iocId)?.verdict_correct ?? true
}
function iocNote(iocId: number): string {
	return iocState.value.get(iocId)?.note ?? ""
}
function setIocCorrect(iocId: number, val: boolean) {
	const cur = iocState.value.get(iocId) ?? { verdict_correct: true, note: "" }
	iocState.value.set(iocId, { ...cur, verdict_correct: val })
}
function setIocNote(iocId: number, val: string) {
	const cur = iocState.value.get(iocId) ?? { verdict_correct: true, note: "" }
	iocState.value.set(iocId, { ...cur, note: val })
}

function verdictColor(verdict: string) {
	if (verdict === "malicious") return "danger"
	if (verdict === "suspicious") return "warning"
	if (verdict === "clean") return "success"
	return undefined
}

function seedIocDefaults() {
	// Any IOC not yet in state defaults to "verdict correct". Preserves
	// per-IOC state hydrated from an existing review.
	for (const ioc of iocs.value) {
		if (!iocState.value.has(ioc.id)) {
			iocState.value.set(ioc.id, { verdict_correct: true, note: "" })
		}
	}
}

async function loadIocs() {
	loading.value = true

	try {
		const iocsRes = await Api.aiAnalyst.getIocsByReport(report.value.id)
		if (iocsRes.data.success) iocs.value = iocsRes.data.iocs || []
		seedIocDefaults()
	} catch (err: unknown) {
		const e = err as { response?: { data?: { message?: string } }; message?: string }
		message.error(e.response?.data?.message || e.message || "Failed to load review data")
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadIocs()
})
</script>
