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
			<n-spin v-model:show="updating" class="flex min-h-80" content-class="flex flex-col grow">
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

						<n-button :loading="updating" type="success" @click="updateIntegration()">
							<template #icon>
								<Icon :name="UpdateIcon"></Icon>
							</template>
							Submit
						</n-button>
					</div>
				</div>
			</n-spin>
		</n-collapse-transition>
	</div>
</template>

<script setup lang="ts">
import type { UpdateIntegrationPayload } from "@/api/endpoints/integrations"
import type { CustomerIntegration } from "@/types/integrations.d"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import _uniqBy from "lodash/uniqBy"
import {
	type FormInst,
	type FormRules,
	NButton,
	NCollapseTransition,
	NForm,
	NFormItem,
	NInput,
	NSpin,
	useDialog,
	useMessage
} from "naive-ui"
import { computed, ref } from "vue"
import { handleDeleteIntegration } from "./utils"

const { integration } = defineProps<{
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
const dialog = useDialog()
const message = useMessage()
const form = ref<FormInst | null>(null)
const model = ref<Record<string, string>>({})
const mode = ref<"view" | "edit">("view")
const deleting = ref<boolean>(false)
const updating = ref<boolean>(false)
const authKeys = ref(getAuthKeys(integration))

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

function handleDelete() {
	handleDeleteIntegration({
		integration,
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
		customer_code: integration.customer_code,
		integration_name: integration.integration_service_name,
		integration_auth_keys: Object.entries(model.value).map(([key, val]) => ({
			auth_key_name: key,
			auth_value: val
		}))
	}

	Api.integrations
		.updateIntegration(payload)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Active Response invoked successfully")
				emit("updated", integration)
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
