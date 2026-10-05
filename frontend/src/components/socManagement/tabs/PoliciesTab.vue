<template>
	<!-- One segmented surface: the scope rail on the left picks what the segments on the right edit. -->
	<div
		class="border-default bg-default overflow-hidden rounded-lg border lg:grid lg:grid-cols-[260px_minmax(0,1fr)]"
		data-testid="soc-policies"
	>
		<ScopeSelector
			v-model="scope"
			v-model:search="search"
			:options="scopeOptions"
			:calendars
			:panel-id="PANEL_ID"
			class="bg-secondary border-default border-b lg:border-r lg:border-b-0"
		/>

		<div
			:id="PANEL_ID"
			class="divide-border flex min-w-0 flex-col divide-y"
			role="tabpanel"
			:aria-label="scope ? `${scopeName} SLA policy` : 'Global SLA policy'"
		>
			<PanelSegment :title="scope ? `${scopeName} — overrides` : 'Global policy'" :caption="scopeCaption">
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

				<template v-if="isAdmin" #footer>
					<label class="flex items-center gap-2 text-sm">
						<n-switch v-model:value="applyToOpen" size="small" data-testid="policy-apply-open" />
						<span>Apply to items still open</span>
						<n-tooltip style="max-width: 320px">
							<template #trigger>
								<Icon name="carbon:information" :size="14" class="text-tertiary cursor-help" />
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
				</template>
			</PanelSegment>

			<CalendarPanel :scope :scope-name :is-admin @changed="codes => (calendars = new Set(codes))" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type { EditablePolicyCell } from "../utils"
import type { PolicyOverride } from "@/types/soc-management"
import { NAlert, NButton, NPopconfirm, NSpin, NSwitch, NTooltip, useMessage } from "naive-ui"
import { computed, onBeforeMount, shallowRef, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { useAuthStore } from "@/stores/auth"
import CalendarPanel from "../policies/CalendarPanel.vue"
import PolicyMatrixEditor from "../policies/PolicyMatrixEditor.vue"
import ScopeSelector from "../policies/ScopeSelector.vue"
import PanelSegment from "../ui/PanelSegment.vue"
import { buildPolicyPayload, cellError, isPolicyDirty, toEditableCells } from "../utils"

const emit = defineEmits<{ (e: "saved"): void }>()

/** The editor panel the scope tabs control. */
const PANEL_ID = "soc-policy-panel"

const message = useMessage()
const isAdmin = computed(() => useAuthStore().isAdmin)
const { options: customerOptions, load: loadCustomers } = useCustomerOptions()

const scope = shallowRef<string | null>(null)
const search = shallowRef("")
const overrides = shallowRef<PolicyOverride[]>([])
/** Customers with business hours of their own, for the scope markers. */
const calendars = shallowRef(new Set<string>())
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
