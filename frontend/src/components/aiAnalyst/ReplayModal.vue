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
					<code class="text-primary">#{{ report.alert_id }}</code> with a forced template. The
					replay creates its own new job and report via Talon — nothing on this report is
					modified.
				</div>

				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" bright>
						<template #label>Customer</template>
						<template #value>{{ report.customer_code }}</template>
					</Badge>
				</div>

				<div>
					<div class="mb-2 font-medium">Choose a template</div>
					<div v-if="!loading && !templates.length">
						<n-empty description="No templates available" class="min-h-20 justify-center" />
					</div>
					<div v-else class="flex max-h-80 flex-col gap-2 overflow-y-auto pr-1">
						<CardEntity
							v-for="tpl of templates"
							:key="tpl.filename"
							size="small"
							embedded
							hoverable
							clickable
							:highlighted="selectedFilename === tpl.filename"
							@click="selectedFilename = tpl.filename"
						>
							<template #default>
								<div class="flex flex-col gap-1">
									<div class="flex items-center gap-2">
										<Icon
											:name="
												selectedFilename === tpl.filename
													? RadioOnIcon
													: RadioOffIcon
											"
											:size="16"
										/>
										<code class="text-primary">{{ tpl.filename }}</code>
									</div>
									<div v-if="tpl.first_line" class="text-secondary text-sm">
										{{ tpl.first_line }}
									</div>
								</div>
							</template>
							<template #footer>
								<div class="text-tertiary flex items-center gap-3 text-xs">
									<span>{{ formatBytes(tpl.size_bytes) }}</span>
									<span>·</span>
									<span>updated {{ formatDate(tpl.modified_at, "MMM D, YYYY HH:mm") }}</span>
								</div>
							</template>
						</CardEntity>
					</div>
				</div>
			</div>
		</n-spin>

		<template #action>
			<div class="flex w-full items-center justify-end gap-3">
				<n-button :disabled="submitting" @click="showLocal = false">Cancel</n-button>
				<n-button
					type="primary"
					:disabled="!selectedFilename || submitting"
					:loading="submitting"
					@click="handleReplay"
				>
					Replay
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { AiAnalystReport } from "@/types/aiAnalyst.d"
import type { TalonTemplate } from "@/types/talon.d"
import { NButton, NEmpty, NModal, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { formatBytes, formatDate } from "@/utils/format"

const props = defineProps<{
	show: boolean
	report: AiAnalystReport
}>()

const emit = defineEmits<{
	(e: "update:show", v: boolean): void
	(e: "replayed", data: Record<string, unknown> | undefined): void
}>()

const RadioOnIcon = "carbon:radio-button-checked"
const RadioOffIcon = "carbon:radio-button"

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
