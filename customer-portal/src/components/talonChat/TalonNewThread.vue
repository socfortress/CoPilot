<template>
	<form class="border-default bg-default flex flex-col gap-4 rounded-lg border p-4" data-testid="talon-new-thread" @submit.prevent="start()">
		<h2 class="m-0 text-base font-semibold">{{ $t("talonChat.newThread.title") }}</h2>

		<p v-if="!customers.length" class="text-secondary m-0 text-sm" data-testid="talon-new-thread-none">
			{{ $t("talonChat.newThread.noCustomers") }}
		</p>

		<template v-else>
			<!-- One organization: it is the conversation's, nothing to choose. -->
			<div v-if="customers.length === 1" class="flex flex-col gap-1 text-sm">
				<span class="text-secondary text-xs">{{ $t("talonChat.newThread.customerLabel") }}</span>
				<span class="font-medium" data-testid="talon-new-thread-customer">{{ customers[0]?.customer_name }}</span>
			</div>
			<label v-else class="flex flex-col gap-1 text-sm">
				<span class="text-secondary text-xs">{{ $t("talonChat.newThread.customerLabel") }}</span>
				<n-select
					v-model:value="customerCode"
					:options
					filterable
					:filter="filterCustomer"
					:render-label="renderCustomerLabel"
					:placeholder="$t('talonChat.newThread.customerPlaceholder')"
					:disabled="creating"
					data-testid="talon-new-thread-select"
				/>
			</label>

			<n-alert v-if="errorCode" type="error" :bordered="false" data-testid="talon-new-thread-error">
				{{ errorText(errorCode) }}
			</n-alert>

			<div class="flex flex-wrap gap-2">
				<n-button type="primary" attr-type="submit" :loading="creating" :disabled="creating || !customerCode" data-testid="talon-new-thread-start">
					{{ $t("talonChat.newThread.start") }}
				</n-button>
				<n-button v-if="cancellable" secondary :disabled="creating" data-testid="talon-new-thread-cancel" @click="emit('cancel')">
					{{ $t("talonChat.newThread.cancel") }}
				</n-button>
			</div>
		</template>
	</form>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { PortalCustomer } from "@/types/auth"
import type { TalonChatThread } from "@/types/talonChat"
import { NAlert, NButton, NSelect } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import { useCustomers } from "@/composables/common/useCustomers"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { useLocalesStore } from "@/stores/i18n"
import { errorCodeOf, errorText } from "./talonChat"

/**
 * A new "Ask Talon" conversation. Every portal conversation is one organization's (talon-analyst
 * FR-API-34): the user picks it among those with Ask Talon on, preselected when there is one.
 * Read-only customers count: chatting is reading.
 */
const { customers, cancellable = false } = defineProps<{
	/** The user's customers with Ask Talon on. */
	customers: PortalCustomer[]
	cancellable?: boolean
}>()

const emit = defineEmits<{ created: [thread: TalonChatThread]; cancel: [] }>()

const { filterCustomer, renderCustomerLabel } = useCustomers()
const { invalidate } = useTalonChatAvailability()
// The thread answers in the portal's language (talon-analyst FR-API-34); CoPilot validates it.
const localesStore = useLocalesStore()

const options = computed<SelectOption[]>(() =>
	customers.map(customer => ({ label: customer.customer_name, value: customer.customer_code }))
)
const customerCode = ref<string | null>(null)
const creating = ref(false)
const errorCode = ref<string | null>(null)

watch(
	() => customers.map(customer => customer.customer_code),
	codes => {
		if (customerCode.value && codes.includes(customerCode.value)) return
		customerCode.value = codes.length === 1 ? (codes[0] ?? null) : null
	},
	{ immediate: true }
)

async function start() {
	if (!customerCode.value || creating.value) return
	creating.value = true
	errorCode.value = null
	try {
		const res = await Api.talonChat.createThread({ customer_code: customerCode.value, language: localesStore.locale })
		emit("created", res.data)
	} catch (err) {
		errorCode.value = errorCodeOf(err) ?? "unknown"
		if (errorCode.value === "portal_off") invalidate(customerCode.value ?? undefined)
	} finally {
		creating.value = false
	}
}
</script>
