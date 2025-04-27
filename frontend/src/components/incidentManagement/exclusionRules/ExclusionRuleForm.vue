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
					<n-form-item path="field_matches" required label="Field matches" :show-feedback="false">
						<div class="flex w-full flex-col gap-4">
							<div
								v-for="(field, index) of model.field_matches"
								:key="field.id"
								class="border-default relative flex w-full flex-col gap-2 rounded-xl border p-2"
							>
								<n-input v-model:value.trim="field.key" placeholder="Field name" clearable />
								<n-input
									v-model:value.trim="field.value"
									placeholder="Field match"
									clearable
									type="textarea"
									:autosize="{ minRows: 3 }"
								/>
								<div class="absolute -right-2.5 -top-2.5">
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

					<n-alert v-if="!areFieldsFilled" type="warning">
						<span class="text-sm">Please fill in all fields</span>
					</n-alert>
					<n-alert v-if="!areFieldsUniques && model.field_matches.length > 1" type="warning">
						<span class="text-sm">Attention, there are duplicate fields</span>
					</n-alert>
				</div>

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
						<n-button type="primary" :disabled="!isValid" :loading="loading" @click="validate()">
							Submit
						</n-button>
					</div>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import type { ExclusionRulePayload } from "@/api/endpoints/incidentManagement/exclusionRules"
import type { Customer } from "@/types/customers.d"
import type { ExclusionRule } from "@/types/incidentManagement/exclusionRules"
import type { FormInst, FormItemRule, FormRules, FormValidationError } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import _get from "lodash/get"
import _trim from "lodash/trim"
import { NAlert, NButton, NCheckbox, NForm, NFormItem, NInput, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, onMounted, ref, toRefs, watch } from "vue"

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
}>()

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: ExclusionRule): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const { entity, resetOnSubmit } = toRefs(props)

const DelIcon = "carbon:close-filled"
const AddIcon = "carbon:add"
const loading = ref(false)
const loadingCustomers = ref(false)
const message = useMessage()
const model = ref<Model>(getDefaultModel())
const formRef = ref<FormInst | null>(null)
const customersList = ref<Customer[]>([])

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

const areFieldsPresent = computed(() => {
	return !!model.value.field_matches.length
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
	},
	field_matches: {
		required: false,

		validator(_rule: FormItemRule, _value: string) {
			if (!areFieldsPresent.value) {
				return new Error(`Please fill least one fields`)
			}

			if (!areFieldsFilled.value) {
				return new Error(`Please fill all fields`)
			}

			if (!areFieldsUniques.value) {
				return new Error(`There are duplicated fields`)
			}

			return true
		},
		trigger: ["input", "blur"]
	}
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

function getDefaultModel(entity?: Partial<ExclusionRule>): Model {
	return {
		name: entity?.name || "",
		description: entity?.description || "",
		channel: entity?.channel || "",
		title: entity?.title || "",
		field_matches: entity?.field_matches
			? Object.entries(entity.field_matches).map(o => ({ key: o[0], value: o[1], id: o[0] }))
			: [{ id: `${new Date().getTime()}`, key: null, value: null }],
		customer_code: entity?.customer_code || undefined,
		enabled: entity?.enabled || false
	}
}

function reset(force?: boolean) {
	if (!loading.value || force) {
		setModel()
		formRef.value?.restoreValidation()
	}
}

function addField() {
	model.value.field_matches.push({
		id: `${new Date().getTime()}`,
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

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function setModel() {
	model.value = getDefaultModel(entity.value)
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

onBeforeMount(() => {
	getCustomers()
})

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>
