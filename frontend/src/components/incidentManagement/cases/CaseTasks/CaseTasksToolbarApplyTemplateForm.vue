<template>
	<n-form label-placement="top">
		<n-form-item label="Template">
			<n-select
				v-model:value="selectedTemplateId"
				:options="templateOptions"
				placeholder="Pick a template to apply"
				:loading="loadingTemplates"
				:render-label="renderOption"
				to="body"
				size="large"
				filterable
			/>
		</n-form-item>
		<p class="text-xs">
			Adds the template's tasks to this case. Existing tasks are preserved — you can layer multiple templates over
			a single investigation.
		</p>
		<div class="mt-6 flex justify-end gap-2">
			<n-button
				type="primary"
				:loading="applySubmitting"
				:disabled="selectedTemplateId === null"
				@click="submitApplyTemplate"
			>
				Apply
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CaseTemplate } from "@/types/incidentManagement/case-templates"
import { NButton, NForm, NFormItem, NSelect, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	caseId: number
	customerCode?: string | null
}>()

const emit = defineEmits<{
	(e: "success"): void
}>()

const message = useMessage()

const applySubmitting = ref(false)
const loadingTemplates = ref(false)
const availableTemplates = ref<CaseTemplate[]>([])
const selectedTemplateId = ref<number | null>(null)

const templateOptions = computed(() =>
	availableTemplates.value.map(t => ({
		label: t.name,
		name: t.name,
		customer_code: t.customer_code,
		source: t.source,
		is_default: t.is_default,
		value: t.id
	}))
)

function renderOption(option: {
	label: string
	value: number
	name?: string | null
	is_default?: boolean
	customer_code?: string | null
	source?: string | null
}) {
	const title = `${option.name}${option.is_default ? " (default)" : ""}`
	const description = [option.customer_code, option.source].filter(Boolean).join(" — ")
	return h("div", { class: "flex flex-col gap-0.5 leading-none py-2" }, [
		h("span", title),
		h("span", { class: "text-secondary text-xs" }, description)
	])
}

function openApplyTemplate() {
	selectedTemplateId.value = null
	loadingTemplates.value = true

	Api.incidentManagement.caseTemplates
		.listTemplates({
			customerCode: props.customerCode ?? undefined,
			includeGlobal: true
		})
		.then(res => {
			if (res.data.success) {
				availableTemplates.value = res.data.templates
			} else {
				message.warning(res.data.message)
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load templates")
		})
		.finally(() => {
			loadingTemplates.value = false
		})
}

async function submitApplyTemplate() {
	if (selectedTemplateId.value === null) return

	applySubmitting.value = true

	try {
		const res = await Api.incidentManagement.caseTemplates.applyTemplateToCase(
			props.caseId,
			selectedTemplateId.value
		)
		if (res.data.success) {
			message.success(`Applied template — ${res.data.tasks_added} task(s) added`)
			emit("success")
		} else {
			message.warning(res.data.message)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to apply template")
	} finally {
		applySubmitting.value = false
	}
}

onBeforeMount(() => {
	openApplyTemplate()
})
</script>
