<template>
	<div class="flex flex-col">
		<n-collapse-transition :show="mode === 'view'">
			<div class="flex min-h-80 grow flex-col justify-between gap-5">
				<div class="grid-auto-fit-200 grid gap-2">
					<CardKV v-for="ak of authKeys" :key="ak.key">
						<template #key>
							{{ ak.key }}
						</template>
						<template #value>
							{{ ak.value || "-" }}
						</template>
					</CardKV>
				</div>

				<div class="flex items-center justify-end gap-3">
					<n-button :loading="updating" :disabled="deleting" secondary @click.stop="switchMode('edit')">
						<template #icon>
							<Icon :name="EditIcon"></Icon>
						</template>
						Edit
					</n-button>

					<n-button type="error" :loading="deleting" secondary @click.stop="handleDelete">
						<template #icon>
							<Icon :name="DeleteIcon"></Icon>
						</template>
						Delete
					</n-button>
				</div>
			</div>
		</n-collapse-transition>
		<n-collapse-transition :show="mode === 'edit'">
			<n-spin v-model:show="updating" class="flex min-h-80" content-class="flex grow flex-col">
				<div class="flex grow flex-col justify-between gap-5">
					<n-form ref="form" :rules :label-width="80" :model>
						<div class="flex flex-wrap gap-2">
							<div v-for="(_, key) of model" :key class="min-w-72 grow">
								<n-form-item :label="key" :path="key">
									<n-input v-model:value="model[key]" :placeholder="`${key}...`" clearable />
								</n-form-item>
							</div>
						</div>
					</n-form>

					<div class="flex items-center justify-between gap-3">
						<n-button secondary @click="switchMode('view')">
							<template #icon>
								<Icon :name="BackIcon"></Icon>
							</template>
							Back
						</n-button>

						<div class="flex items-center justify-end gap-3">
							<n-button :disabled="updating" @click="reset()">Reset</n-button>

							<n-button :loading="updating" type="success" :disabled="!isValid" @click="validate()">
								<template #icon>
									<Icon :name="UpdateIcon"></Icon>
								</template>
								Submit
							</n-button>
						</div>
					</div>
				</div>
			</n-spin>
		</n-collapse-transition>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules, FormValidationError } from "naive-ui"
import type { IntegrationAuthKeyPairs, UpdateIntegrationPayload } from "@/api/endpoints/integrations"
import type { CustomerIntegration } from "@/types/integrations.d"
import _uniqBy from "lodash/uniqBy"
import { NButton, NCollapseTransition, NForm, NFormItem, NInput, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { handleDeleteIntegration } from "./utils"

const props = defineProps<{
	integration: CustomerIntegration
}>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: CustomerIntegration): void
}>()

const EditIcon = "uil:edit-alt"
const BackIcon = "carbon:arrow-left"
const DeleteIcon = "ph:trash"
const UpdateIcon = "carbon:save"
const integration = ref(props.integration)
const dialog = useDialog()
const message = useMessage()
const form = ref<FormInst | null>(null)
const model = ref<Record<string, string | null>>({})
const mode = ref<"view" | "edit">("view")
const deleting = ref<boolean>(false)
const updating = ref<boolean>(false)
const authKeys = ref(getAuthKeys(integration.value))

const rules = computed(() =>
	authKeys.value.reduce((acc, cur) => {
		acc[cur.key] = {
			required: true,
			message: `Please insert the ${cur.key}`,
			trigger: ["input", "blur"]
		}
		return acc
	}, {} as FormRules)
)

const isValid = computed(() => {
	let valid = true

	for (const field of Object.entries(model.value)) {
		if (!field[1]) {
			valid = false
		}
	}

	return valid
})

function validate() {
	if (!form.value) return

	form.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			updateIntegration()
		} else {
			message.warning("You must fill in the required fields correctly.")
			return false
		}
	})
}

function getAuthKeys(integration: CustomerIntegration) {
	const keys: { key: string; value: string }[] = []

	for (const subscriptions of integration.integration_subscriptions) {
		for (const ak of subscriptions.integration_auth_keys) {
			keys.push({
				key: ak.auth_key_name,
				value: ak.auth_value
			})
		}
	}

	return _uniqBy(keys, "key")
}

function updateAuthKeys(integrationAuthKeys: IntegrationAuthKeyPairs[]) {
	for (const subscriptions of integration.value.integration_subscriptions) {
		for (const ak of subscriptions.integration_auth_keys) {
			const ia = integrationAuthKeys.find(i => i.auth_key_name === ak.auth_key_name)
			ak.auth_value = ia?.auth_value || ak.auth_value
		}
	}

	authKeys.value = getAuthKeys(integration.value)

	return integration.value
}

function switchMode(newMode: "view" | "edit") {
	mode.value = newMode

	if (newMode === "edit") {
		model.value = authKeys.value.reduce(
			(acc, cur) => {
				acc[cur.key] = cur.value
				return acc
			},
			{} as Record<string, string>
		)
	}
}

function reset() {
	model.value = authKeys.value.reduce(
		(acc, cur) => {
			acc[cur.key] = null
			return acc
		},
		{} as Record<string, string | null>
	)
}

function handleDelete() {
	handleDeleteIntegration({
		integration: integration.value,
		cbBefore: () => {
			deleting.value = true
		},
		cbSuccess: () => {
			emit("deleted")
		},
		cbAfter: () => {
			deleting.value = false
		},
		message,
		dialog
	})
}

function updateIntegration() {
	updating.value = true

	const payload: UpdateIntegrationPayload = {
		customer_code: integration.value.customer_code,
		integration_name: integration.value.integration_service_name,
		integration_auth_keys: Object.entries(model.value).map(([key, val]) => ({
			auth_key_name: key,
			auth_value: val || ""
		}))
	}

	Api.integrations
		.updateIntegration(payload)
		.then(res => {
			if (res.data?.success) {
				message.success(res.data?.message || "Customer integration successfully updated")

				if (res.data?.additional_info) {
					message.info(res.data.additional_info, { duration: 0, closable: true })
				}

				emit("updated", updateAuthKeys(payload.integration_auth_keys))
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			updating.value = false
		})
}
</script>
