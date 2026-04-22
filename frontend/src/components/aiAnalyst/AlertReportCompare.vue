<template>
	<n-spin :show="loading" class="min-h-40">
		<div class="flex flex-col gap-4">
			<div v-if="!loading && reports.length < 2">
				<n-empty
					description="Only one report exists for this alert. Replay with a different template to generate a second report to compare."
					class="min-h-40 justify-center"
				/>
			</div>

			<template v-else>
				<div class="text-secondary text-sm">
					Side-by-side view of two investigations for alert
					<code class="text-primary">#{{ alertId }}</code>. Pick any two runs below — defaults
					to the current report on the left and the next-most-recent run on the right.
				</div>

				<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
					<!-- Side A -->
					<div class="flex flex-col gap-3">
						<div>
							<div class="mb-1 font-medium">Version A</div>
							<n-select
								v-model:value="idA"
								:options="reportOptions"
								:render-label="renderOption"
							/>
						</div>
						<ReportColumn v-if="reportA" :report="reportA" />
					</div>

					<!-- Side B -->
					<div class="flex flex-col gap-3">
						<div>
							<div class="mb-1 font-medium">Version B</div>
							<n-select
								v-model:value="idB"
								:options="reportOptions"
								:render-label="renderOption"
							/>
						</div>
						<ReportColumn v-if="reportB" :report="reportB" />
					</div>
				</div>
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystReport } from "@/types/aiAnalyst.d"
import { h } from "vue"
import { NEmpty, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import { formatDate } from "@/utils/format"
import ReportColumn from "./AlertReportCompareColumn.vue"

const props = defineProps<{
	alertId: number
	currentReportId?: number
}>()

const { alertId, currentReportId } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const reports = ref<AiAnalystReport[]>([])

const idA = ref<number | null>(null)
const idB = ref<number | null>(null)

const reportOptions = computed(() =>
	reports.value.map(r => ({
		label: r.id.toString(),
		value: r.id,
		severity: r.severity_assessment,
		created_at: r.created_at
	}))
)

// Render option with created_at + severity so the picker shows meaningful
// distinctions between runs rather than just bare IDs.
function renderOption(option: {
	label: string
	value: number
	severity?: string | null
	created_at?: string
}) {
	const ts = option.created_at ? String(formatDate(option.created_at, "MMM D, YYYY HH:mm")) : ""
	const sev = option.severity ? ` · ${option.severity}` : ""
	return h("div", { class: "flex flex-col" }, [
		h("span", `#${option.label}${sev}`),
		h("span", { class: "text-secondary text-xs" }, ts)
	])
}

const reportA = computed(() => reports.value.find(r => r.id === idA.value) ?? null)
const reportB = computed(() => reports.value.find(r => r.id === idB.value) ?? null)

async function loadReports() {
	loading.value = true
	try {
		const res = await Api.aiAnalyst.getReportsByAlert(alertId.value)
		if (res.data.success) {
			// Newest first — backend already sorts by created_at desc, but we
			// re-sort defensively in case that changes.
			const sorted = [...(res.data.reports || [])].sort(
				(a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
			)
			reports.value = sorted
			if (sorted.length >= 2) {
				// Default A to the currentReportId if provided (so the user always
				// sees "this report" on the left), otherwise newest.
				const preferA = currentReportId?.value
					? sorted.find(r => r.id === currentReportId.value)?.id
					: sorted[0].id
				idA.value = preferA ?? sorted[0].id
				idB.value = sorted.find(r => r.id !== idA.value)?.id ?? sorted[1].id
			}
		} else {
			message.warning(res.data.message || "Failed to load reports")
		}
	} catch (err: unknown) {
		const e = err as { response?: { data?: { message?: string } }; message?: string }
		message.error(e.response?.data?.message || e.message || "Failed to load reports")
	} finally {
		loading.value = false
	}
}

watch(alertId, () => loadReports())

onBeforeMount(() => {
	loadReports()
})
</script>
