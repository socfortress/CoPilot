<template>
	<n-form :disabled="loading" label-placement="top">
		<n-form-item v-if="hasMultipleCustomers" :label="$t('common.fields.customer')" required>
			<n-select
				v-model:value="model.customer_code"
				data-testid="case-customer"
				:options="customerOptions"
				:render-label="renderCustomerLabel"
				:filter="filterCustomer"
				filterable
				:placeholder="$t('cases.createCaseForm.placeholders.customer')"
			/>
		</n-form-item>
		<n-form-item :label="$t('cases.createCaseForm.fields.caseName')" required>
			<n-input v-model:value="model.case_name" :placeholder="$t('cases.createCaseForm.placeholders.caseName')" />
		</n-form-item>
		<n-form-item :label="$t('cases.createCaseForm.fields.caseStatus')" required>
			<n-select v-model:value="model.case_status" :options="statusOptions" :placeholder="$t('cases.createCaseForm.placeholders.caseStatus')" />
		</n-form-item>
		<n-form-item :label="$t('cases.createCaseForm.fields.caseDescription')" required>
			<n-input
				v-model:value="model.case_description"
				type="textarea"
				:autosize="{ minRows: 4, maxRows: 8 }"
				:placeholder="$t('cases.createCaseForm.placeholders.caseDescription')"
			/>
		</n-form-item>
		<n-form-item :label="$t('cases.createCaseForm.fields.assignedTo')">
			<n-select
				v-model:value="model.assigned_to"
				:options="assignedToOptions"
				:loading="optionsLoading"
				clearable
				filterable
				:placeholder="$t('cases.createCaseForm.placeholders.assignedTo')"
			/>
		</n-form-item>
		<div class="flex justify-end gap-3">
			<n-button :disabled="loading" @click="emit('cancel')">{{ $t("common.actions.cancel") }}</n-button>
			<n-button type="primary" :loading :disabled="!isValidForm" @click="handleSubmit">
				{{ $t("cases.createCaseForm.submit") }}
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { CasePayload } from "@/api/endpoints/cases"
import type { ApiError } from "@/types/common"
import { NButton, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import { useCustomerPrefill } from "@/composables/common/useCustomerPrefill"
import { getApiErrorMessage } from "@/utils"
import { SETTABLE_STATUSES, workflowStatusLabel } from "@/utils/workflowStatus"

const emit = defineEmits<{
	(e: "success"): void
	(e: "cancel"): void
}>()

const message = useMessage()
const { t } = useI18n()
const { customerOptions, filterCustomer, renderCustomerLabel, hasMultipleCustomers, initialCustomerCode } =
	useCustomerPrefill({ writable: true })
const loading = ref(false)
const optionsLoading = ref(false)
const assignedToOptions = ref<{ label: string; value: string }[]>([])
// Computed, so the labels follow a language change.
const statusOptions = computed(() => SETTABLE_STATUSES.map(value => ({ label: workflowStatusLabel(value), value })))

function emptyModel(): CasePayload {
	return {
		case_name: "",
		case_description: "",
		assigned_to: undefined,
		case_status: "OPEN",
		// Seeded from the global customer filter (or the only accessible customer); a
		// multi-tenant user with no unambiguous default has to pick one explicitly.
		customer_code: initialCustomerCode() ?? undefined
	}
}

const model = ref<CasePayload>(emptyModel())

/** Clear the fields and re-seed the customer. The parent calls this on every modal open. */
function reset() {
	if (loading.value) return
	model.value = emptyModel()
}

defineExpose({ reset })

const isValidForm = computed(
	() =>
		model.value.case_name.trim().length > 0 &&
		model.value.case_description.trim().length > 0 &&
		Boolean(model.value.case_status) &&
		Boolean(model.value.customer_code)
)

async function loadAssignedToOptions() {
	optionsLoading.value = true

	try {
		const response = await Api.cases.getCasesFilters()
		assignedToOptions.value = response.data.assigned_to.map(o => ({ label: o, value: o }))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		optionsLoading.value = false
	}
}

async function handleSubmit() {
	if (!isValidForm.value || loading.value) return

	loading.value = true

	try {
		const response = await Api.cases.createCase({
			case_name: model.value.case_name.trim(),
			case_description: model.value.case_description.trim(),
			assigned_to: model.value.assigned_to || undefined,
			case_status: model.value.case_status,
			customer_code: model.value.customer_code
		})
		message.success(response.data.message || t("cases.createCaseForm.created"))
		emit("success")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadAssignedToOptions()
})
</script>
