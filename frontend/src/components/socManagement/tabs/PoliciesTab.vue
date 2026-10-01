<template>
	<div class="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]" data-testid="soc-policies">
		<SocPanel title="Scope" caption="global, or a customer override" flush>
			<n-input v-model:value="search" size="small" placeholder="Find a customer" clearable class="m-3 w-auto!">
				<template #prefix><Icon name="carbon:search" :size="14" /></template>
			</n-input>
			<nav class="scope-list flex max-h-[520px] flex-col overflow-y-auto pb-2" aria-label="Policy scope">
				<button
					v-for="option of scopeOptions"
					:key="option.key"
					type="button"
					class="scope-option flex items-center justify-between gap-2 px-3 py-2 text-left text-sm transition-colors"
					:class="{ 'is-active': option.code === scope }"
					:data-testid="`policy-scope-${option.key}`"
					@click="scope = option.code"
				>
					<span class="flex min-w-0 flex-col leading-tight">
						<span class="truncate">{{ option.label }}</span>
						<span v-if="option.code" class="text-tertiary text-2xs font-mono">{{ option.code }}</span>
					</span>
					<n-tag v-if="option.overrides" size="tiny" type="warning" :bordered="false" round>
						{{ option.overrides }} override{{ option.overrides === 1 ? "" : "s" }}
					</n-tag>
				</button>
			</nav>
		</SocPanel>

		<SocPanel :title="scope ? `${scopeName} — overrides` : 'Global policy'" :caption="scopeCaption">
			<template #actions>
				<n-popconfirm v-if="isAdmin && scope && hasOverride" @positive-click="removeOverride">
					<template #trigger>
						<n-button
							size="tiny"
							quaternary
							type="error"
							:loading="removing"
							data-testid="policy-remove-override"
						>
							<template #icon><Icon name="carbon:reset" /></template>
							Follow global
						</n-button>
					</template>
					Remove every override of {{ scope }}? It will follow the global policy again.
				</n-popconfirm>
			</template>

			<n-alert v-if="!isAdmin" type="info" :bordered="false" class="mb-4" data-testid="policy-readonly">
				SLA targets are a commitment to customers: only administrators can change them.
			</n-alert>
			<n-alert v-if="loadError" type="error" :bordered="false" class="mb-4">
				Could not load the policy: {{ loadError }}
			</n-alert>

			<n-spin :show="loading">
				<PolicyMatrixEditor
					v-model="cells"
					:original
					:scope="scope ? 'customer' : 'global'"
					:readonly="!isAdmin"
				/>
			</n-spin>

			<footer
				v-if="isAdmin"
				class="border-default mt-5 flex flex-wrap items-center justify-between gap-3 border-t pt-4"
			>
				<label class="flex items-center gap-2 text-sm">
					<n-switch v-model:value="applyToOpen" size="small" data-testid="policy-apply-open" />
					<span>Apply to items still open</span>
					<n-tooltip style="max-width: 320px">
						<template #trigger>
							<Icon name="carbon:information" :size="14" class="text-tertiary" />
						</template>
						Open items keep the targets they opened with unless you ask. Clocks already met or breached
						never change.
					</n-tooltip>
				</label>
				<div class="flex items-center gap-2">
					<n-button size="small" :disabled="!dirty || saving" @click="discard">Discard</n-button>
					<n-button
						size="small"
						type="primary"
						:disabled="!dirty || hasErrors"
						:loading="saving"
						data-testid="policy-save"
						@click="save"
					>
						<template #icon><Icon name="carbon:save" /></template>
						Save {{ scope ? "overrides" : "policy" }}
					</n-button>
				</div>
			</footer>
		</SocPanel>
	</div>
</template>

<script setup lang="ts">
import type { EditablePolicyCell } from "../utils"
import type { PolicyOverride } from "@/types/soc-management"
import { NAlert, NButton, NInput, NPopconfirm, NSpin, NSwitch, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, onBeforeMount, shallowRef, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { useAuthStore } from "@/stores/auth"
import PolicyMatrixEditor from "../policies/PolicyMatrixEditor.vue"
import SocPanel from "../ui/SocPanel.vue"
import { buildPolicyPayload, cellError, isPolicyDirty, toEditableCells } from "../utils"

const emit = defineEmits<{ (e: "saved"): void }>()

const message = useMessage()
const isAdmin = computed(() => useAuthStore().isAdmin)
const { options: customerOptions, load: loadCustomers } = useCustomerOptions()

const scope = shallowRef<string | null>(null)
const search = shallowRef("")
const overrides = shallowRef<PolicyOverride[]>([])
const original = shallowRef<EditablePolicyCell[]>([])
const cells = shallowRef<EditablePolicyCell[]>([])
const applyToOpen = shallowRef(false)
const loading = shallowRef(false)
const saving = shallowRef(false)
const removing = shallowRef(false)
const loadError = shallowRef<string | null>(null)

const overrideCount = computed(() => new Map(overrides.value.map(o => [o.customer_code, o.cells])))
const hasOverride = computed(() => !!scope.value && overrideCount.value.has(scope.value))
const dirty = computed(() => isPolicyDirty(cells.value, original.value))
const hasErrors = computed(() => cells.value.some(cell => cellError(cell)))

const scopeOptions = computed(() => {
	const needle = search.value.trim().toLowerCase()
	const customers = customerOptions.value
		.map(option => ({
			key: String(option.value),
			code: String(option.value),
			label: String(option.label).replace(/\s*\([^)]*\)$/, "")
		}))
		.filter(
			option =>
				!needle || option.label.toLowerCase().includes(needle) || option.code.toLowerCase().includes(needle)
		)
		.map(option => ({ ...option, overrides: overrideCount.value.get(option.code) ?? 0 }))
		.sort((a, b) => b.overrides - a.overrides || a.label.localeCompare(b.label))
	return [{ key: "global", code: null as string | null, label: "Global policy", overrides: 0 }, ...customers]
})

const scopeName = computed(() => scopeOptions.value.find(option => option.code === scope.value)?.label ?? scope.value)
const scopeCaption = computed(() =>
	scope.value ? "cells not overridden follow the global policy" : "cells left at default follow the built-in targets"
)

function errorText(err: unknown) {
	const e = err as { response?: { data?: { detail?: string; message?: string } }; message?: string }
	return e?.response?.data?.detail ?? e?.response?.data?.message ?? e?.message ?? "unknown error"
}

async function loadPolicy() {
	loading.value = true
	loadError.value = null
	try {
		const response = await Api.socManagement.getPolicy(scope.value)
		original.value = toEditableCells(response.data.policy)
		cells.value = original.value.map(cell => ({ ...cell }))
	} catch (err) {
		loadError.value = errorText(err)
	} finally {
		loading.value = false
	}
}

async function loadOverrides() {
	try {
		overrides.value = (await Api.socManagement.getPolicyOverrides()).data.overrides
	} catch {
		overrides.value = [] // markers are a nicety; the editor still works
	}
}

async function save() {
	saving.value = true
	try {
		const response = await Api.socManagement.savePolicy(
			buildPolicyPayload(cells.value, scope.value, applyToOpen.value)
		)
		original.value = toEditableCells(response.data.policy)
		cells.value = original.value.map(cell => ({ ...cell }))
		message.success(response.data.message || "Policy saved")
		applyToOpen.value = false
		await loadOverrides()
		emit("saved")
	} catch (err) {
		message.error(`Could not save: ${errorText(err)}`)
	} finally {
		saving.value = false
	}
}

async function removeOverride() {
	if (!scope.value) return
	removing.value = true
	try {
		const response = await Api.socManagement.deletePolicyOverride(scope.value, applyToOpen.value)
		original.value = toEditableCells(response.data.policy)
		cells.value = original.value.map(cell => ({ ...cell }))
		message.success(response.data.message || "Overrides removed")
		await loadOverrides()
		emit("saved")
	} catch (err) {
		message.error(`Could not remove the overrides: ${errorText(err)}`)
	} finally {
		removing.value = false
	}
}

function discard() {
	cells.value = original.value.map(cell => ({ ...cell }))
}

watch(scope, loadPolicy)

onBeforeMount(() => {
	loadPolicy()
	loadOverrides()
	loadCustomers()
})
</script>

<style scoped>
.scope-option {
	border-left: 2px solid transparent;
}

.scope-option:hover {
	background-color: var(--hover-color);
}

.scope-option.is-active {
	border-left-color: var(--primary-color);
	background-color: rgb(var(--primary-color-rgb) / 0.08);
}
</style>
