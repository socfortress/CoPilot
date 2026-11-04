<template>
	<form class="flex grow flex-col items-center justify-center gap-4 px-6 py-10 text-center" data-testid="talon-new-thread" @submit.prevent="start()">
		<span class="hero" aria-hidden="true"><Icon name="carbon:chat-bot" :size="28" /></span>
		<div class="flex max-w-lg flex-col gap-2">
			<h2 class="font-display m-0 text-2xl leading-tight font-semibold tracking-tight">{{ $t("talonChat.newThread.title") }}</h2>
			<p class="text-secondary m-0 text-sm leading-6">{{ $t("talonChat.page.intro") }}</p>
		</div>

		<p v-if="!customers.length" class="text-secondary m-0 text-sm" data-testid="talon-new-thread-none">
			{{ $t("talonChat.newThread.noCustomers") }}
		</p>

		<template v-else>
			<!-- One organization: it is the conversation's, nothing to choose. -->
			<div v-if="customers.length === 1" class="text-secondary flex items-center gap-2 text-sm">
				<span>{{ $t("talonChat.newThread.customerLabel") }}</span>
				<span class="text-default font-medium" data-testid="talon-new-thread-customer">{{ customers[0]?.customer_name }}</span>
			</div>
			<label v-else class="flex w-full max-w-xs flex-col gap-1 text-left text-sm">
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

			<n-alert v-if="errorCode" type="error" :bordered="false" class="w-full max-w-md text-left" data-testid="talon-new-thread-error">
				{{ errorText(errorCode) }}
			</n-alert>

			<div class="flex flex-wrap justify-center gap-2">
				<n-button type="primary" attr-type="submit" :loading="creating" :disabled="creating || !customerCode" data-testid="talon-new-thread-start">
					<template #icon><Icon name="carbon:add" /></template>
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
import Icon from "@/components/common/Icon.vue"
import { useCustomers } from "@/composables/common/useCustomers"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { useLocalesStore } from "@/stores/i18n"
import { errorCodeOf, errorText } from "./talonChat"

/**
 * A new "Ask Talon" conversation. Every portal conversation is one organization's (talon-analyst
 * FR-API-34): the user picks it among those with Ask Talon on, preselected when there is one.
 * Read-only customers count: chatting is reading. Shown where the open conversation would be, as
 * the page's welcome when none is open.
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

<style scoped>
.hero {
	display: flex;
	width: 56px;
	height: 56px;
	align-items: center;
	justify-content: center;
	border-radius: 16px;
	background: rgba(var(--primary-color-rgb) / 0.16);
	color: var(--primary-color);
}
</style>
