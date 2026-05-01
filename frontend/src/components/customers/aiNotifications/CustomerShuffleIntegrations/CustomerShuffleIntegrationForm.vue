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

		<!--
			Shuffle Org picker. Phase 3a: dropdown of orgs the deployment's
			admin Bearer can see, populated from /api/notifications/shuffle/orgs.
			Manual entry stays as a fallback for offline use, restricted
			networks, or when an org is too new to appear in the listing yet.
		-->
		<n-form-item label="Shuffle org" path="shuffle_org_id">
			<div class="flex w-full flex-col gap-2">
				<n-select
					v-model:value="form.shuffle_org_id"
					:options="orgOptions"
					:loading="loadingOrgs"
					:disabled="manualEntry"
					filterable
					placeholder="Pick a Shuffle org"
					@update:value="onOrgPicked"
				/>

				<div class="flex items-center gap-3 text-xs">
					<n-button size="tiny" quaternary :disabled="loadingOrgs" @click="loadOrgs(true)">
						<template #icon>
							<Icon :name="RefreshIcon" :size="12" />
						</template>
						Refresh list
					</n-button>
					<n-checkbox v-model:checked="manualEntry" size="small">
						Don't see your org? Enter the ID manually
					</n-checkbox>
				</div>

				<n-input
					v-if="manualEntry"
					v-model:value="form.shuffle_org_id"
					placeholder="6b6f65a4-d8f8-48ef-b02f-23a4a5f73e4a"
					:maxlength="64"
				/>

				<div v-if="orgsError" class="text-error text-xs">
					Couldn't fetch orgs from Shuffle: {{ orgsError }}. Use manual entry above.
				</div>
			</div>
			<template #feedback>
				<span class="text-tertiary text-xs">
					Sent as the <code>Org-Id</code> header on every dispatch — scopes the
					Shuffle call to the right org's authenticated apps.
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
import type { ShuffleIntegration, ShuffleIntegrationPayload, ShuffleOrg } from "@/types/notifications.d"
import type { FormInst, FormRules } from "naive-ui"
import { NButton, NCheckbox, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, reactive, ref } from "vue"
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
const RefreshIcon = "carbon:renew"

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const editing = computed(() => props.editingIntegration !== null)

const form = reactive<ShuffleIntegrationPayload>({
	display_name: props.editingIntegration?.display_name ?? "",
	shuffle_org_id: props.editingIntegration?.shuffle_org_id ?? "",
	enabled: props.editingIntegration?.enabled ?? true
})

// Org-picker state. We default to dropdown mode; manual entry is a
// one-checkbox escape hatch for cases where the Shuffle listing call
// fails or the desired org doesn't appear in the list.
const orgs = ref<ShuffleOrg[]>([])
const loadingOrgs = ref(false)
const orgsError = ref<string | null>(null)
const manualEntry = ref(false)

const orgOptions = computed(() =>
	orgs.value.map(o => {
		// Show the name with a short Org-Id suffix so admins can disambiguate
		// when two orgs share a display name. Sub-orgs get an extra hint so
		// it's obvious which rows are children of the parent (typical Shuffle
		// pattern: one parent org per MSP, one sub-org per customer).
		const idHint = `(${o.id.slice(0, 8)}…)`
		const subOrgHint = o.creator_org ? " · sub-org" : ""
		return {
			label: `${o.name} ${idHint}${subOrgHint}`,
			value: o.id
		}
	})
)

async function loadOrgs(force = false) {
	if (loadingOrgs.value) return
	loadingOrgs.value = true
	orgsError.value = null
	try {
		const res = await Api.notifications.listShuffleOrgs()
		if (res.data.success) {
			orgs.value = res.data.orgs
			// If we're editing and the existing org_id isn't in the list,
			// fall through to manual entry so the form stays usable.
			if (
				editing.value &&
				form.shuffle_org_id &&
				!orgs.value.some(o => o.id === form.shuffle_org_id)
			) {
				manualEntry.value = true
			}
		} else {
			orgsError.value = res.data.message || "Unknown error"
			manualEntry.value = true
		}
	} catch (err: unknown) {
		orgsError.value = getApiErrorMessage(err as never) || "Network error"
		manualEntry.value = true
	} finally {
		loadingOrgs.value = false
	}
	if (force) {
		message.success(`${orgs.value.length} org(s) loaded`)
	}
}

function onOrgPicked(_orgId: string | null) {
	// No-op for now — kept as a hook in case Phase 3b wants to chain
	// the picker into automatic display-name population.
}

const rules: FormRules = {
	display_name: { required: true, message: "Name is required", trigger: ["input", "blur"] },
	shuffle_org_id: {
		required: true,
		message: "Pick a Shuffle org or enter an Org-Id manually",
		trigger: ["input", "change", "blur"]
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

onBeforeMount(() => {
	loadOrgs()
})
</script>
