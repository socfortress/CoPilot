<template>
	<div class="mx-auto flex w-full max-w-md flex-col gap-4 py-8" data-testid="talon-v2-new-thread">
		<div class="flex flex-col gap-1">
			<div class="text-default text-base font-semibold">New thread</div>
			<div class="text-tertiary text-xs">
				A thread works on one customer's data, or on none. That choice is fixed when the thread starts.
			</div>
		</div>

		<div class="flex flex-col gap-1">
			<label class="text-secondary text-xs" for="talon-v2-new-thread-customer">Customer</label>
			<n-select
				v-model:value="form.customer"
				input-id="talon-v2-new-thread-customer"
				:options
				:loading="customersLoading"
				filterable
				data-testid="talon-v2-new-thread-customer"
			/>
			<div v-if="unassigned" class="text-warning text-xs" data-testid="talon-v2-new-thread-unassigned">
				No customers are assigned to you yet, so only a general thread is possible.
			</div>
		</div>

		<div class="flex flex-col gap-1">
			<label class="text-secondary text-xs" for="talon-v2-new-thread-title">Title (optional)</label>
			<n-input
				v-model:value="form.title"
				:input-props="{ id: 'talon-v2-new-thread-title' }"
				:maxlength="TITLE_MAX"
				placeholder="What is this thread about?"
				data-testid="talon-v2-new-thread-title"
				@keydown.enter.prevent="submit()"
			/>
		</div>

		<n-alert v-if="error" type="error" :bordered="false" class="text-sm" data-testid="talon-v2-new-thread-error">
			{{ error }}
		</n-alert>

		<div class="flex justify-end gap-2">
			<n-button v-if="cancellable" secondary :disabled="creating" @click="emit('cancel')">Cancel</n-button>
			<n-button
				type="primary"
				:loading="creating"
				:disabled="creating"
				data-testid="talon-v2-new-thread-create"
				@click="submit()"
			>
				Start thread
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
// The new-thread picker: the caller's customers (`GET /customers`, already scoped to them), plus
// "General (no customer data)", prefilled from the global sidebar filter. CoPilot checks the
// choice again before talon-analyst is asked (M5-5a); the scope can't change after.
import type { SelectOption } from "naive-ui"
import type { TalonV2ThreadCreate } from "@/types/talonV2"
import { NAlert, NButton, NInput, NSelect } from "naive-ui"
import { computed, onMounted, reactive, ref, watch } from "vue"
import Api from "@/api"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"

const {
	creating = false,
	error = null,
	cancellable = true
} = defineProps<{
	creating?: boolean
	error?: string | null
	cancellable?: boolean
}>()

const emit = defineEmits<{
	(e: "create", value: TalonV2ThreadCreate): void
	(e: "cancel"): void
}>()

/** The select's value for a general thread (`customer_code: null`). */
const GENERAL = "__general__"
const TITLE_MAX = 200

const { options: customerOptions, loading: customersLoading, load: loadCustomers } = useCustomerOptions()
const { applyGlobalCustomerPrefill } = useGlobalCustomerFilter()

const form = reactive<{ customer: string; title: string }>({ customer: GENERAL, title: "" })
const unassigned = ref(false)
let prefilled = false

const options = computed<SelectOption[]>(() => [
	{ label: "General (no customer data)", value: GENERAL },
	...customerOptions.value
])
const customerCodes = computed(() => customerOptions.value.map(option => String(option.value)))

/** Once the customers are known: the global filter's first one the caller can pick, else General. */
function prefill() {
	if (prefilled || !customerCodes.value.length) return
	prefilled = true
	const seeded = applyGlobalCustomerPrefill("customer", { customer: null } as Record<string, unknown>, {
		availableCustomerCodes: customerCodes.value
	})
	const code = typeof seeded.customer === "string" ? seeded.customer : null
	if (code && customerCodes.value.includes(code) && form.customer === GENERAL) form.customer = code
}

watch(customerCodes, prefill)

onMounted(async () => {
	loadCustomers().then(prefill)
	try {
		const res = await Api.auth.getMyCustomerAccess()
		unassigned.value = res.data?.scope === "unassigned"
	} catch {
		// Only a hint.
	}
})

function submit() {
	if (creating) return
	const title = form.title.trim()
	emit("create", {
		title: title || null,
		customer_code: form.customer === GENERAL ? null : form.customer
	})
}
</script>
