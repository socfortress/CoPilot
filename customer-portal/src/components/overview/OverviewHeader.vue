<template>
	<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
		<div class="flex min-w-0 flex-col gap-1.5">
			<h1 class="title font-display">Security overview</h1>
			<p class="text-secondary text-sm">
				Your organization's security posture and the latest activity from the SOC.
			</p>
		</div>

		<div class="text-tertiary flex items-center gap-4 font-mono text-xs">
			<span class="flex items-center gap-1.5" :title="scopeTitle">
				<Icon name="carbon:filter" :size="14" />
				<span class="max-w-60 truncate">{{ scopeLabel }}</span>
			</span>
			<span v-if="lastUpdated" class="tabular-nums">updated {{ formatDate(lastUpdated, dFormats.time) }}</span>
			<n-button
				size="small"
				quaternary
				:disabled="refreshing"
				aria-label="Refresh overview"
				@click="emit('refresh')"
			>
				<template #icon>
					<Icon name="carbon:renew" :class="{ 'animate-spin': refreshing }" />
				</template>
			</n-button>
		</div>
	</header>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

defineProps<{
	lastUpdated: Date | null
	refreshing: boolean
}>()

const emit = defineEmits<{
	(e: "refresh"): void
}>()

const authStore = useAuthStore()
const customerFilterStore = useCustomerFilterStore()
const dFormats = useSettingsStore().dateFormat

// What the numbers below are scoped to: the global filter's selection, or every
// customer the user can see.
const scopeCodes = computed(() =>
	customerFilterStore.selectedCustomerCodes.length
		? customerFilterStore.selectedCustomerCodes
		: authStore.accessibleCustomerCodes
)

const scopeLabel = computed(() => {
	if (!customerFilterStore.selectedCustomerCodes.length && authStore.accessibleCustomerCodes.length > 1) {
		return `all customers (${authStore.accessibleCustomerCodes.length})`
	}
	return scopeCodes.value.join(", ") || "no customer"
})

const scopeTitle = computed(() => `Scope: ${scopeCodes.value.join(", ")}`)
</script>

<style lang="scss" scoped>
.title {
	font-size: 1.5rem;
	font-weight: 600;
	line-height: 1.15;
	letter-spacing: -0.02em;
	text-wrap: balance;
}
</style>
