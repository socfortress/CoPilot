<template>
	<n-form ref="formRef" :model="form" :rules label-placement="top" class="flex flex-col gap-1.5">
		<div v-if="kind === 'network_zone'" class="grid grid-cols-1 gap-4 md:grid-cols-2">
			<n-form-item label="Range" path="cidr">
				<n-input v-model:value="form.cidr" placeholder="e.g. 10.20.0.0/24" :maxlength="CIDR_MAX" />
			</n-form-item>
			<n-form-item label="Zone" path="zone">
				<n-select v-model:value="form.zone" :options="ZONE_OPTIONS" placeholder="Pick a zone" />
			</n-form-item>
		</div>

		<div v-else-if="kind === 'public_range'" class="grid grid-cols-1 gap-4 md:grid-cols-2">
			<n-form-item label="Range" path="cidr">
				<n-input
					v-model:value="form.cidr"
					placeholder="A public IP address or CIDR range"
					:maxlength="CIDR_MAX"
				/>
			</n-form-item>
			<n-form-item label="Used for" path="use">
				<n-select v-model:value="form.use" :options="USE_OPTIONS" placeholder="Pick a use" />
			</n-form-item>
		</div>

		<template v-else-if="kind === 'asset_role'">
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				<n-form-item label="Host" path="host">
					<n-input v-model:value="form.host" placeholder="e.g. dc01" :maxlength="NAME_MAX" />
				</n-form-item>
				<n-form-item label="Role" path="role">
					<n-select v-model:value="form.role" :options="ROLE_OPTIONS" placeholder="Pick a role" filterable />
				</n-form-item>
			</div>
			<n-form-item label="Owner (optional)" path="owner">
				<n-input v-model:value="form.owner" placeholder="e.g. Finance IT" :maxlength="NAME_MAX" />
			</n-form-item>
			<n-form-item :show-feedback="false">
				<n-checkbox v-model:checked="form.crownJewel">Crown jewel</n-checkbox>
			</n-form-item>
			<div class="text-secondary mb-2 text-xs">One of the hosts this customer can least afford to lose.</div>
		</template>

		<template v-else>
			<n-form-item label="What" path="what">
				<n-select v-model:value="form.what" :options="EXPECTED_OPTIONS" placeholder="Pick what is expected" />
			</n-form-item>
			<div class="text-secondary mb-2 text-xs">
				Name at least one host or source range. talon-analyst only shows this fact when all of it matches the
				alert, so be exact.
			</div>
			<n-form-item ref="hostsItem" label="Hosts" path="hosts">
				<n-dynamic-input
					v-model:value="form.hosts"
					:on-create="() => ''"
					:max="LIST_MAX"
					placeholder="e.g. scanner01"
					class="w-full"
				>
					<template #create-button-default>Add a host</template>
				</n-dynamic-input>
			</n-form-item>
			<n-form-item label="Source ranges" path="sourceCidrs">
				<n-dynamic-input
					v-model:value="form.sourceCidrs"
					:on-create="() => ''"
					:max="LIST_MAX"
					placeholder="e.g. 10.20.0.5 or 10.20.0.0/24"
					class="w-full"
				>
					<template #create-button-default>Add a source range</template>
				</n-dynamic-input>
			</n-form-item>
			<n-form-item label="Accounts (optional)" path="accounts">
				<n-dynamic-input
					v-model:value="form.accounts"
					:on-create="() => ''"
					:max="LIST_MAX"
					placeholder="e.g. svc-scanner"
					class="w-full"
				>
					<template #create-button-default>Add an account</template>
				</n-dynamic-input>
			</n-form-item>
		</template>

		<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
			<n-form-item v-if="kind === 'expected_activity'" label="Starts" path="startsAt">
				<n-date-picker v-model:value="form.startsAt" type="datetime" clearable class="w-full" />
			</n-form-item>
			<n-form-item
				ref="expiresItem"
				:label="kind === 'expected_activity' ? 'Expires' : 'Expires (optional)'"
				path="expiresAt"
			>
				<n-date-picker v-model:value="form.expiresAt" type="datetime" clearable class="w-full" />
			</n-form-item>
		</div>
		<div v-if="kind === 'expected_activity'" class="text-secondary mb-2 text-xs">
			Expected activity has to expire. It can run for {{ EXPECTED_MAX_DAYS }} days at most, ending no later than {{ EXPECTED_MAX_DAYS }} days from now.
		</div>

		<n-form-item label="Note (optional)" path="note">
			<n-input
				v-model:value="form.note"
				type="textarea"
				:autosize="{ minRows: 2, maxRows: 4 }"
				:maxlength="NOTE_MAX"
				show-count
				placeholder="Anything else an analyst should know"
			/>
		</n-form-item>

		<div class="flex flex-wrap items-center justify-end gap-2">
			<n-button @click="emit('close')">Cancel</n-button>
			<n-button type="primary" :loading="submitting" data-testid="knowledge-form-save" @click="submit">
				{{ editingFact ? "Save changes" : "Add fact" }}
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormItemInst } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { KnowledgeItem, KnowledgeKind } from "@/types/customer-knowledge"
import {
	NButton,
	NCheckbox,
	NDatePicker,
	NDynamicInput,
	NForm,
	NFormItem,
	NInput,
	NSelect,
	useMessage
} from "naive-ui"
import { reactive, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import {
	buildBody,
	CIDR_MAX,
	emptyForm,
	EXPECTED_MAX_DAYS,
	EXPECTED_OPTIONS,
	formFromItem,
	knowledgeRules,
	LIST_MAX,
	NAME_MAX,
	NOTE_MAX,
	refusalText,
	ROLE_OPTIONS,
	USE_OPTIONS,
	ZONE_OPTIONS
} from "./knowledge"

const { customerCode, kind, editingFact } = defineProps<{
	customerCode: string
	kind: KnowledgeKind
	editingFact: KnowledgeItem | null
}>()

const emit = defineEmits<{
	(e: "submitted"): void
	(e: "close"): void
	(e: "stale"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const hostsItem = ref<FormItemInst | null>(null)
const expiresItem = ref<FormItemInst | null>(null)
const submitting = ref(false)

const form = reactive(editingFact ? formFromItem(editingFact) : emptyForm(kind))
const rules = knowledgeRules(form, editingFact ? formFromItem(editingFact) : null)

// These two fields answer for a neighbour too, so a change there settles what they last said.
watch(
	() => form.sourceCidrs,
	() => hostsItem.value?.restoreValidation(),
	{ deep: true }
)
watch(
	() => form.startsAt,
	() => expiresItem.value?.restoreValidation()
)

async function submit() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	submitting.value = true
	try {
		const body = buildBody(form)
		const res = editingFact
			? await Api.customerKnowledge.update(customerCode, editingFact.id, {
					...body,
					expected_version: editingFact.version
				})
			: await Api.customerKnowledge.create(customerCode, body)

		if (res.data.success) {
			message.success("Fact saved")
			// Not refusals: the fact is saved, and these are what the SOC should look at.
			for (const warning of res.data.warnings ?? []) message.warning(warning, { duration: 8000 })
			emit("submitted")
		} else {
			message.warning(res.data.message || "Couldn't save this fact")
		}
	} catch (err) {
		const text = refusalText(getApiErrorMessage(err as ApiError)) || "Couldn't save this fact"
		// Saving again can't work: the list has to give the analyst the latest version first.
		if (editingFact && (err as ApiError).response?.status === 409) {
			message.warning(text, { duration: 8000 })
			emit("stale")
			return
		}
		// A refusal says why, in words for the analyst, and the form stays open to fix it.
		message.error(text, { duration: 8000 })
	} finally {
		submitting.value = false
	}
}
</script>
