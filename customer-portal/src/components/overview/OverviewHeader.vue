<template>
	<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
		<div class="flex min-w-0 flex-col gap-1.5">
			<h1 class="font-display text-2xl leading-tight font-semibold tracking-tight text-balance">
				{{ $t("overview.header.title") }}
			</h1>
			<p class="text-secondary text-sm">
				{{ $t("overview.header.subtitle") }}
			</p>
		</div>

		<div class="text-tertiary flex items-center gap-4 font-mono text-xs">
			<span class="flex items-center gap-1.5" :title="scopeTitle">
				<Icon name="carbon:filter" :size="14" />
				<span class="max-w-60 truncate" data-testid="overview-scope">{{ scopeLabel }}</span>
			</span>
			<span v-if="lastUpdated" class="tabular-nums">
				{{ $t("overview.header.updated", { time: formatDate(lastUpdated, dFormats.time) }) }}
			</span>
			<n-button
				size="small"
				quaternary
				:disabled="refreshing"
				:aria-label="$t('overview.header.refresh')"
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
import { useI18n } from "vue-i18n"
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

const { t } = useI18n()
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
		return t("overview.header.scopeAll", { count: authStore.accessibleCustomerCodes.length })
	}
	return scopeCodes.value.map(code => authStore.customerName(code)).join(", ") || t("overview.header.scopeNone")
})

// The tooltip names each customer with its code, which is what support quotes.
const scopeTitle = computed(() =>
	t("overview.header.scopeTitle", {
		customers: scopeCodes.value
			.map(code => {
				const name = authStore.customerName(code)
				return name === code ? code : `${name} (${code})`
			})
			.join(", ")
	})
)
</script>
