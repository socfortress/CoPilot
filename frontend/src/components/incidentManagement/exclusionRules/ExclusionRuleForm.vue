<template>
	<n-spin :show="loading" class="customer-form">
		<n-form ref="formRef" :label-width="80" :model :rules>
			<div class="flex flex-col gap-0">
				<n-form-item label="Name" path="name">
					<n-input v-model:value.trim="model.name" placeholder="Exclusion rule name" clearable />
				</n-form-item>

				<n-form-item label="Description" path="description">
					<n-input
						v-model:value.trim="model.description"
						placeholder="Exclusion rule description"
						clearable
					/>
				</n-form-item>

				<n-form-item label="Channel" path="channel">
					<n-input v-model:value.trim="model.channel" placeholder="Exclusion rule channel" clearable />
				</n-form-item>

				<n-form-item label="Title" path="title">
					<n-input v-model:value.trim="model.title" placeholder="Exclusion rule title" clearable />
				</n-form-item>

				<div class="mb-6 flex flex-col gap-2">
					<!--
						In-context creation (#934): the originating alert's EventData fields, named
						exactly as the backend matcher looks them up. Ticking one adds a match row
						pinned to the observed value; the analyst can still loosen it below
						(e.g. a `regex:` prefix) before saving.
					-->
					<n-form-item v-if="candidateFields?.length" label="Fields from alert" :show-feedback="false">
						<div class="border-default flex w-full flex-col gap-1 rounded-xl border p-2">
							<div
								v-for="field of candidateFields"
								:key="field.name"
								class="flex items-start gap-2 rounded-lg px-1 py-0.5"
								:class="{ 'opacity-60': field.volatile }"
							>
								<n-checkbox
									:checked="isCandidateSelected(field.name)"
									@update:checked="toggleCandidate(field, $event)"
								>
									<span class="font-mono text-sm">{{ field.name }}</span>
								</n-checkbox>
								<n-tag v-if="field.volatile" size="tiny" :bordered="false" type="warning">
									volatile
								</n-tag>
								<span
									class="text-secondary min-w-0 grow truncate font-mono text-xs"
									:title="field.value"
								>
									{{ field.value }}
								</span>
							</div>
						</div>
					</n-form-item>

					<n-form-item required label="Field matches" :show-feedback="false">
						<div class="flex w-full flex-col gap-4">
							<div
								v-for="(field, index) of model.field_matches"
								:key="field.id"
								class="border-default relative flex w-full flex-col gap-2 rounded-xl border p-2"
							>
								<n-input
									v-model:value.trim="field.key"
									placeholder="Field name"
									clearable
									:status="fieldStatus(field, 'key')"
								/>
								<n-input
									v-model:value.trim="field.value"
									placeholder="Field match"
									clearable
									type="textarea"
									:autosize="{ minRows: 3 }"
									:status="fieldStatus(field, 'value')"
								/>
								<div class="absolute -top-2.5 -right-2.5">
									<n-button
										v-if="model.field_matches.length > 1"
										circle
										secondary
										size="tiny"
										type="error"
										@click="delField(index)"
									>
										<template #icon>
											<Icon :name="DelIcon" />
										</template>
									</n-button>
								</div>
							</div>
						</div>
					</n-form-item>

					<div class="flex justify-end">
						<n-button @click="addField()">
							<template #icon>
								<Icon :name="AddIcon" />
							</template>
							Add field
						</n-button>
					</div>

					<n-alert v-if="!areFieldsPresent" type="warning">
						<span class="text-sm">Add at least one field match</span>
					</n-alert>
					<n-alert v-if="!areFieldsFilled" type="warning">
						<span class="text-sm">Please fill in all fields</span>
					</n-alert>
					<n-alert v-if="!areFieldsUniques && model.field_matches.length > 1" type="warning">
						<span class="text-sm">Attention, there are duplicate fields</span>
					</n-alert>
				</div>

				<!--
					Live check against the originating alert. While a request is in flight the previous
					result is kept but dimmed and a spinner is shown, so the banner never claims a
					verdict for a rule the backend has not seen yet.
				-->
				<n-alert
					v-if="sourceAlertId && (dryRun || dryRunPending)"
					:type="dryRunPending ? 'default' : dryRun?.matches ? 'success' : 'warning'"
					class="mb-6"
				>
					<template v-if="dryRunPending">
						<div class="flex items-center gap-3">
							<n-spin :size="14" />
							<span class="text-sm">Checking against alert #{{ sourceAlertId }}…</span>
						</div>
					</template>
					<template v-else-if="dryRun?.matches">
						<span class="text-sm">
							This rule matches alert #{{ sourceAlertId }}: the next identical alert will be suppressed.
						</span>
					</template>
					<template v-else-if="dryRun">
						<span class="text-sm">This rule would NOT have suppressed alert #{{ sourceAlertId }}:</span>
						<ul class="mt-1 list-disc pl-5 text-sm">
							<li v-for="reason of dryRun.reasons" :key="reason">{{ reason }}</li>
						</ul>
					</template>
				</n-alert>

				<n-form-item label="Customer" path="customer_code">
					<n-select
						v-model:value="model.customer_code"
						:options="customersOptions"
						placeholder="Select Customer..."
						to="body"
						filterable
						:loading="loadingCustomers || !customersOptions.length"
					/>
				</n-form-item>

				<n-form-item path="enabled" label="Status">
					<n-checkbox v-model:checked="model.enabled" size="large">Enabled</n-checkbox>
				</n-form-item>

				<div class="flex justify-between gap-4">
					<div class="flex gap-4">
						<slot name="additionalActions"></slot>
					</div>
					<div class="flex gap-4">
						<n-button :disabled="loading" @click="reset()">Reset</n-button>
						<n-button type="primary" :disabled="!isValid" :loading @click="validate()">Submit</n-button>
					</div>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormRules, FormValidationError } from "naive-ui"
import type { ExclusionRulePayload } from "@/api/endpoints/incidentManagement/exclusion-rules"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type {
	ExclusionRule,
	ExclusionRuleDraftField,
	ExclusionRuleDryRunResult
} from "@/types/incidentManagement/exclusion-rules"
import axios from "axios"
import _debounce from "lodash/debounce"
import _get from "lodash/get"
import _trim from "lodash/trim"
import { NAlert, NButton, NCheckbox, NForm, NFormItem, NInput, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { getApiErrorMessage } from "@/utils"

interface FieldMatch {
	id: string
	key: string | null
	value: string | null
}

interface Model extends Omit<ExclusionRulePayload, "field_matches"> {
	field_matches: FieldMatch[]
}

const props = defineProps<{
	entity?: ExclusionRule
	resetOnSubmit?: boolean
	/** Initial values for a NEW rule (in-context creation from an alert). Ignored when `entity` is set. */
	prefill?: Partial<ExclusionRulePayload>
	/** The originating alert's EventData fields, offered as one-click `field_matches`. */
	candidateFields?: ExclusionRuleDraftField[]
	/** When set, every edit is dry-run against this alert so the analyst sees whether the rule catches it. */
	sourceAlertId?: number
}>()

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: ExclusionRule): void
}>()

const { entity, resetOnSubmit, prefill, candidateFields, sourceAlertId } = toRefs(props)
const { applyGlobalCustomerPrefill } = useGlobalCustomerFilter()
const DelIcon = "carbon:close-filled"
const AddIcon = "carbon:add"
const loading = ref(false)
const loadingCustomers = ref(false)
const message = useMessage()
const model = ref<Model>(getDefaultModel())
const formRef = ref<FormInst | null>(null)
const customersList = ref<Customer[]>([])
const dryRun = ref<ExclusionRuleDryRunResult | null>(null)
/** True from the first edit until the backend answers — covers the debounce wait AND the request. */
const dryRunPending = ref(false)
let dryRunAbort: AbortController | null = null

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

// The model always carries one empty placeholder row so the UI has something to type into,
// so "present" must mean "at least one row with a name" — counting rows let a rule with no
// field matches at all through a validator that says the opposite.
const areFieldsPresent = computed(() => {
	return model.value.field_matches.some(o => !!o.key)
})

const areFieldsFilled = computed(() => {
	const fieldsFilled = model.value.field_matches.filter(o => (!!o.key && !o.value) || (!o.key && !!o.value))

	return fieldsFilled.length === 0
})

const areFieldsUniques = computed(() => {
	const fieldsFilled = model.value.field_matches.filter(o => !!o.key).map(o => o.key)

	const uniques: (string | null)[] = fieldsFilled.filter((value, index, self) => self.indexOf(value) === index)

	return uniques.length === fieldsFilled.length
})

const rules: FormRules = {
	name: {
		required: true,
		message: "Please input name",
		trigger: ["input", "blur"]
	},
	description: {
		required: true,
		message: "Please input description",
		trigger: ["input", "blur"]
	},
	channel: {
		required: true,
		message: "Please input channel",
		trigger: ["input", "blur"]
	},
	title: {
		required: true,
		message: "Please input title",
		trigger: ["input", "blur"]
	}
}

/**
 * Field-match rows are validated per input rather than through an n-form-item rule: an
 * invalid form item paints every input inside it red, so one half-filled pair used to flag
 * the complete pairs next to it. Only the empty half of an incomplete pair is marked, and
 * only once the analyst has started typing in that row. `isValid` still gates Submit.
 */
function fieldStatus(field: FieldMatch, part: "key" | "value"): "error" | undefined {
	const other = part === "key" ? field.value : field.key
	const own = part === "key" ? field.key : field.value
	if (!!other && !own) return "error"
	if (part === "key" && !!own && model.value.field_matches.filter(o => o.key === own).length > 1) return "error"
	return undefined
}

const isValid = computed(() => {
	let valid = true

	for (const key in rules) {
		const rule = rules[key] as FormRules

		if (rule.required && !_trim(_get(model.value, key))) {
			valid = false
		}
	}

	if (!areFieldsFilled.value || !areFieldsPresent.value || !areFieldsUniques.value) {
		valid = false
	}

	return valid
})

function validate() {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			submit()
		} else {
			message.warning("You must fill in the required fields correctly.")
			return false
		}
	})
}

function getDefaultModel(entity?: Partial<ExclusionRule> | Partial<ExclusionRulePayload>): Model {
	const fieldMatches = entity?.field_matches ? Object.entries(entity.field_matches) : []

	return {
		name: entity?.name || "",
		description: entity?.description || "",
		channel: entity?.channel || "",
		title: entity?.title || "",
		field_matches: fieldMatches.length
			? fieldMatches.map(o => ({ key: o[0], value: o[1], id: o[0] }))
			: [{ id: `${Date.now()}`, key: null, value: null }],
		customer_code: entity?.customer_code || undefined,
		enabled: entity?.enabled || false,
		// Provenance rides along untouched; the backend only honours it on create.
		source_alert_id: entity?.source_alert_id ?? undefined
	}
}

function isCandidateSelected(name: string) {
	return model.value.field_matches.some(o => o.key === name)
}

function toggleCandidate(field: ExclusionRuleDraftField, checked: boolean) {
	if (checked) {
		if (isCandidateSelected(field.name)) return
		// Replace a lone empty placeholder row instead of leaving it dangling under the picked field.
		const onlyEmptyRow = model.value.field_matches.length === 1 && !model.value.field_matches[0].key
		if (onlyEmptyRow) model.value.field_matches.splice(0, 1)
		model.value.field_matches.push({ id: field.name, key: field.name, value: field.value })
	} else {
		const index = model.value.field_matches.findIndex(o => o.key === field.name)
		if (index !== -1) delField(index)
	}
}

/**
 * Dry-run against the originating alert. Runs the same matcher the ingest path runs, so
 * a green result means "the next identical alert is suppressed" — not a client-side guess.
 * Debounced because every keystroke in a field value would otherwise fire a request.
 */
const runDryRun = _debounce(() => {
	if (!sourceAlertId.value) return

	const fieldMatches = model.value.field_matches
		.filter(o => !!o.key && !!o.value)
		.reduce((acc: Record<string, string>, cur: FieldMatch) => {
			acc[`${cur.key}`] = `${cur.value}`
			return acc
		}, {})

	if (!model.value.channel && !model.value.title && !Object.keys(fieldMatches).length) {
		dryRun.value = null
		dryRunPending.value = false
		return
	}

	dryRunAbort?.abort()
	dryRunAbort = new AbortController()
	const { signal } = dryRunAbort

	Api.incidentManagement.exclusionRules
		.dryRunExclusionRule(
			sourceAlertId.value,
			{
				channel: model.value.channel || undefined,
				title: model.value.title || undefined,
				customer_code: model.value.customer_code || undefined,
				field_matches: fieldMatches
			},
			signal
		)
		.then(res => {
			if (res.data.success) {
				dryRun.value = { matches: res.data.matches, reasons: res.data.reasons }
			}
		})
		.catch(err => {
			if (axios.isCancel(err)) return
			dryRun.value = null
			message.error(getApiErrorMessage(err as ApiError) || "Could not check the rule against the alert.")
		})
		.finally(() => {
			// A superseded request must not clear the spinner the newer one is still showing.
			if (!signal.aborted) dryRunPending.value = false
		})
}, 400)

function reset(force?: boolean) {
	if (!loading.value || force) {
		setModel()
		formRef.value?.restoreValidation()
	}
}

function addField() {
	model.value.field_matches.push({
		id: `${Date.now()}`,
		key: null,
		value: null
	})
}

function delField(index: number) {
	model.value.field_matches.splice(index, 1)

	if (!model.value.field_matches.length) {
		addField()
	}
}

function getCustomers() {
	loadingCustomers.value = true

	return Api.customers
		.getCustomers({})
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

function submit() {
	loading.value = true

	const payload: ExclusionRulePayload = {
		...model.value,
		field_matches: model.value.field_matches
			.filter(o => !!o.key && !!o.value)
			.reduce((acc: Record<string, string>, cur: FieldMatch) => {
				acc[`${cur.key}`] = `${cur.value}`
				return acc
			}, {})
	}

	const method = entity.value?.id
		? Api.incidentManagement.exclusionRules.updateExclusionRule(entity.value.id, payload)
		: Api.incidentManagement.exclusionRules.createExclusionRule(payload)

	method
		.then(res => {
			if (res.data.success) {
				emit("submitted", res.data.exclusion_response)
				if (resetOnSubmit.value) {
					reset(true)
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function setModel() {
	model.value = getDefaultModel(entity.value ?? prefill.value)
}

watch(loading, val => {
	emit("update:loading", val)
})

watch(
	entity,
	val => {
		if (val) {
			setModel()
		}
	},
	{ immediate: true }
)

watch(
	prefill,
	val => {
		if (val && !entity.value) {
			setModel()
		}
	},
	{ immediate: true }
)

watch(
	model,
	() => {
		if (!sourceAlertId.value) return
		dryRunPending.value = true
		runDryRun()
	},
	{ deep: true, immediate: true }
)

onBeforeUnmount(() => {
	runDryRun.cancel()
	dryRunAbort?.abort()
	dryRunPending.value = false
})

onBeforeMount(() => {
	getCustomers().then(() => {
		applyGlobalCustomerPrefill("customer_code", model.value)
	})
})

defineExpose({
	reset
})
</script>
