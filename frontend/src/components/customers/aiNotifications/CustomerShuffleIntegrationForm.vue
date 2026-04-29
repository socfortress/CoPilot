<template>
	<n-form
		ref="formRef"
		:model="form"
		:rules="rules"
		label-placement="top"
		class="px-7 py-4"
	>
		<div class="mb-3 flex items-center justify-between">
			<h3 class="text-lg font-medium">
				{{ editing ? "Edit Shuffle integration" : "Add Shuffle integration" }}
			</h3>
			<n-button size="small" quaternary @click="$emit('close')">
				<template #icon>
					<Icon :name="CloseIcon" :size="14" />
				</template>
				Cancel
			</n-button>
		</div>

		<n-form-item label="Display name" path="display_name">
			<n-input
				v-model:value="form.display_name"
				placeholder="e.g. Acme Production Shuffle"
				:maxlength="128"
				show-count
			/>
		</n-form-item>

		<n-form-item label="Shuffle Org-Id" path="shuffle_org_id">
			<n-input
				v-model:value="form.shuffle_org_id"
				placeholder="6b6f65a4-d8f8-48ef-b02f-23a4a5f73e4a"
				:maxlength="64"
			/>
			<template #feedback>
				<span class="text-tertiary text-xs">
					Find this on the customer's Shuffle org settings page. Sent as the
					<code>Org-Id</code> header on each dispatch — scopes the Shuffle call
					to the right org's authenticated apps.
				</span>
			</template>
		</n-form-item>

		<n-form-item>
			<n-checkbox v-model:checked="form.enabled">Enabled</n-checkbox>
		</n-form-item>

		<div class="flex justify-end gap-2">
			<n-button @click="$emit('close')">Cancel</n-button>
			<n-button type="primary" :loading="submitting" @click="submit">
				{{ editing ? "Save changes" : "Add integration" }}
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { ShuffleIntegration, ShuffleIntegrationPayload } from "@/types/notifications.d"
import type { FormInst, FormRules } from "naive-ui"
import { NButton, NCheckbox, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { computed, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	customerCode: string
	editingIntegration: ShuffleIntegration | null
}>()

const emit = defineEmits<{
	(e: "submitted"): void
	(e: "close"): void
}>()

const CloseIcon = "carbon:close"

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const editing = computed(() => props.editingIntegration !== null)

const form = reactive<ShuffleIntegrationPayload>({
	display_name: props.editingIntegration?.display_name ?? "",
	shuffle_org_id: props.editingIntegration?.shuffle_org_id ?? "",
	enabled: props.editingIntegration?.enabled ?? true
})

const rules: FormRules = {
	display_name: { required: true, message: "Name is required", trigger: ["input", "blur"] },
	shuffle_org_id: {
		required: true,
		message: "Shuffle Org-Id is required",
		trigger: ["input", "blur"]
	}
}

async function submit() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	submitting.value = true
	try {
		const res = props.editingIntegration
			? await Api.notifications.updateShuffleIntegration(
					props.customerCode,
					props.editingIntegration.id,
					form
				)
			: await Api.notifications.createShuffleIntegration(props.customerCode, form)

		if (res.data.success) {
			message.success(editing.value ? "Integration updated" : "Integration added")
			emit("submitted")
		} else {
			message.warning(res.data.message || "Failed to save integration")
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to save integration")
	} finally {
		submitting.value = false
	}
}
</script>
