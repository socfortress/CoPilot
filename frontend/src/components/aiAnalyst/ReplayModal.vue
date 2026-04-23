<template>
	<n-modal
		v-model:show="showLocal"
		:style="{ maxWidth: 'min(720px, 90vw)' }"
		preset="card"
		title="Replay with different template"
		:bordered="false"
		segmented
	>
		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<div class="text-secondary text-sm">
					Re-runs the investigation for alert
					<code class="text-primary">#{{ report.alert_id }}</code>
					with a forced template. The replay creates its own new job and report via Talon — nothing on this
					report is modified.
				</div>

				<div class="flex flex-col gap-2">
					<div class="flex items-center justify-between gap-2">
						<div class="text-sm">Choose a template</div>
						<Badge type="splitted" bright>
							<template #label>Customer</template>
							<template #value>{{ report.customer_code }}</template>
						</Badge>
					</div>
					<div v-if="!loading && !templates.length">
						<n-empty description="No templates available" class="min-h-20 justify-center" />
					</div>
					<n-radio-group v-else v-model:value="selectedFilename" class="flex! w-full flex-col gap-2">
						<n-radio
							v-for="tpl of templates"
							:key="tpl.filename"
							:value="tpl.filename"
							class="border-default hover:border-primary w-full rounded-lg border p-3 transition-colors [&_.n-radio\_\_label]:grow"
							:class="selectedFilename === tpl.filename ? 'border-primary bg-primary/5' : ''"
						>
							<div class="flex w-full flex-col gap-1 pl-0.5">
								<div class="flex w-full items-center justify-between gap-3">
									<span class="font-medium">{{ tpl.filename }}</span>
									<span class="text-secondary text-xs">{{ formatBytes(tpl.size_bytes) }}</span>
								</div>
								<span class="text-secondary text-xs">
									updated {{ formatDate(tpl.modified_at, "MMM D, YYYY HH:mm") }}
								</span>
							</div>
						</n-radio>
					</n-radio-group>
				</div>
			</div>
		</n-spin>

		<template #action>
			<div class="flex w-full items-center justify-end gap-3">
				<n-button :disabled="submitting" @click="showLocal = false">Cancel</n-button>
				<n-button type="primary" :disabled="!selectedFilename" :loading="submitting" @click="handleReplay">
					Replay
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { AiAnalystReport } from "@/types/aiAnalyst.d"
import type { TalonTemplate } from "@/types/talon.d"
import { NButton, NEmpty, NModal, NRadio, NRadioGroup, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import { formatBytes, formatDate } from "@/utils/format"

const props = defineProps<{
	show: boolean
	report: AiAnalystReport
}>()

const emit = defineEmits<{
	(e: "update:show", v: boolean): void
	(e: "replayed", data: Record<string, unknown> | undefined): void
}>()

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const templates = ref<TalonTemplate[]>([])
const selectedFilename = ref<string | null>(null)

const showLocal = computed({
	get: () => props.show,
	set: (v: boolean) => emit("update:show", v)
})

async function loadTemplates() {
	loading.value = true
	selectedFilename.value = null
	try {
		const res = await Api.talon.getTemplates()
		if (res.data.success) {
			templates.value = res.data.templates || []
		} else {
			message.warning(res.data.message || "Failed to load templates")
			templates.value = []
		}
	} catch (err: unknown) {
		const e = err as { response?: { data?: { message?: string } }; message?: string }
		message.error(e.response?.data?.message || e.message || "Failed to load templates")
		templates.value = []
	} finally {
		loading.value = false
	}
}

async function handleReplay() {
	if (!selectedFilename.value) return
	submitting.value = true
	try {
		const res = await Api.aiAnalyst.replayReport(props.report.id, {
			template_override: selectedFilename.value,
			customer_code: props.report.customer_code,
			sender: "copilot-replay"
		})
		if (res.data.success) {
			message.success(res.data.message || "Replay triggered")
			emit("replayed", res.data.data)
			showLocal.value = false
		} else {
			message.warning(res.data.message || "Failed to trigger replay")
		}
	} catch (err: unknown) {
		const e = err as { response?: { data?: { message?: string } }; message?: string }
		message.error(e.response?.data?.message || e.message || "Failed to trigger replay")
	} finally {
		submitting.value = false
	}
}

// Fetch templates each time the modal is opened — fresh mtime + preview,
// and covers the case where the user adds a template via the palace flow.
watch(
	() => props.show,
	v => {
		if (v) loadTemplates()
	},
	{ immediate: true }
)
</script>
