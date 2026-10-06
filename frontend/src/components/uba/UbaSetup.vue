<template>
	<section class="uba-setup border-default overflow-hidden rounded-lg border" data-testid="uba-setup">
		<header class="bg-secondary border-default flex items-center gap-3 border-b px-4 py-2.5">
			<span class="setup-tile grid size-7 shrink-0 place-items-center rounded-md" aria-hidden="true">
				<Icon name="carbon:settings-adjust" :size="15" />
			</span>
			<span :class="SECTION_LABEL" class="min-w-0 flex-1 truncate">
				{{ registered ? "UBA setup for this customer" : "Set up UBA for this customer" }}
			</span>
			<n-button v-if="closable" size="small" quaternary @click="emit('close')">
				<template #icon><Icon name="carbon:close" :size="14" /></template>
				Close
			</n-button>
		</header>
		<div class="flex flex-col gap-3 px-4 py-4">
			<p v-if="!isAdmin" class="text-secondary m-0 text-sm">
				SOCFortress UBA is not set up for this customer yet. An admin can set it up from this page.
			</p>

			<template v-if="isAdmin">
				<n-spin v-if="loading && !info" class="min-h-16" show />
				<UbaError v-else-if="error" :error />

				<template v-else-if="info">
					<n-alert v-if="info.problem" type="warning" :bordered="false">{{ info.problem }}</n-alert>

					<!-- Registered: the history replay's progress -->
					<div v-else-if="onboarding && onboarding.status !== 'inactive'" class="flex flex-col gap-2">
						<div class="flex flex-wrap items-center gap-2 text-sm">
							<n-tag size="small" :type="statusType" :bordered="false">{{ onboarding.status }}</n-tag>
							<span>{{ statusText }}</span>
						</div>
						<n-progress
							v-if="onboarding.status === 'bootstrapping' || onboarding.status === 'pending'"
							type="line"
							:percentage="progress"
							:show-indicator="false"
							:height="6"
							class="max-w-xl"
						/>
						<n-alert v-if="onboarding.bootstrap_error" type="error" :bordered="false" class="text-xs">
							{{ onboarding.bootstrap_error }}. UBA retries every 10 minutes, and replays this customer's events once
							it succeeds.
						</n-alert>
						<p class="text-secondary max-w-3xl text-sm">
							UBA reads {{ sourceText }} for this customer. After provisioning Microsoft 365 (or another Microsoft
							365 tenant) for it, run setup again so UBA reads the new streams too.
						</p>
						<p v-if="onboarding.status === 'live'" class="text-tertiary max-w-3xl text-xs">
							A source added after the customer went live starts without history: UBA learns its normal activity
							from then on, so expect more first-time findings from it for the first days.
						</p>
					</div>

					<!-- Not registered: what will be created, and the form -->
					<div v-else class="flex flex-col gap-3">
						<p class="text-secondary max-w-3xl text-sm">
							Registers the customer with UBA and routes its events to UBA in Graylog: a UBA FEED stream and
							routing pipeline next to each source stream ({{ sourceText }}), one output to UBA, and the UBA ALERTS
							stream that brings UBA's alerts back. UBA first replays the history you choose with alerting off,
							so it knows what is normal, then scores new activity.
						</p>
						<div class="flex flex-wrap items-end gap-4">
							<n-form-item label="History to learn from" :show-feedback="false" class="w-48">
								<n-select v-model:value="days" :options="DAY_OPTIONS" />
							</n-form-item>
						</div>
					</div>

					<template v-if="!info.problem">
						<n-checkbox v-model:checked="deployRules">
							Also deploy UBA's Wazuh rules (Windows password changes and resets)
						</n-checkbox>
						<n-alert v-if="deployRules" type="warning" :bordered="false" class="text-xs">
							This uploads a rules file and restarts the Wazuh manager. Check afterwards that the log shipper
							(e.g. Fluent Bit) still ships alerts: on some hosts it stops after a manager restart until it is
							restarted too.
						</n-alert>
					</template>

					<div class="flex flex-wrap items-center gap-2">
						<n-button
							v-if="!info.problem"
							:type="registered ? 'default' : 'primary'"
							:size="registered ? 'small' : 'medium'"
							:loading="running"
							@click="run"
						>
							{{ registered ? "Run setup again" : "Set up UBA" }}
						</n-button>
						<span v-if="registered" class="text-tertiary text-xs">
							Repairs missing Graylog objects; never duplicates them.
						</span>
					</div>

					<ul v-if="steps.length" class="m-0 flex list-none flex-col gap-1 p-0 text-xs">
						<li v-for="(s, i) of steps" :key="i" class="flex flex-wrap items-center gap-2">
							<n-tag size="tiny" :bordered="false" :type="s.status === 'skipped' ? 'default' : 'success'">
								{{ s.status }}
							</n-tag>
							<span class="font-mono">{{ s.step }}</span>
							<span v-if="s.detail" class="text-tertiary">{{ s.detail }}</span>
						</li>
					</ul>
				</template>
			</template>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { UbaOnboarding, UbaProvisioning, UbaProvisionStep } from "@/types/uba"
import { NAlert, NButton, NCheckbox, NFormItem, NProgress, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"

const { customerCode, closable = false } = defineProps<{ customerCode: string; closable?: boolean }>()
const emit = defineEmits<{ live: []; close: [] }>()

const DAY_OPTIONS = [
	{ label: "none (start now)", value: 0 },
	{ label: "7 days", value: 7 },
	{ label: "14 days (recommended)", value: 14 },
	{ label: "30 days", value: 30 }
]
const POLL_MS = 15000

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)
const info = ref<UbaProvisioning | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const running = ref(false)
const steps = ref<UbaProvisionStep[]>([])
const days = ref(14)
const deployRules = ref(false)
let poll: ReturnType<typeof setInterval> | null = null

const onboarding = computed<UbaOnboarding | null>(() => info.value?.onboarding ?? null)
const registered = computed(() => !!onboarding.value && onboarding.value.status !== "inactive")

const sourceText = computed(() => {
	const sources = info.value?.sources ?? {}
	const parts = []
	if (sources.WAZUH) parts.push("Wazuh")
	if (sources.O365) {
		const tenants = info.value?.office365_tenants.length ?? 0
		parts.push(`Microsoft 365 (${tenants} tenant${tenants === 1 ? "" : "s"})`)
	}
	return parts.join(" and ") || "none found"
})

const statusType = computed(() => {
	const status = onboarding.value?.status
	return status === "live" ? "success" : status === "error" ? "error" : "info"
})

const progress = computed(() => {
	const o = onboarding.value
	if (!o?.bootstrap_since || !o.bootstrap_cursor) return 0
	const since = Date.parse(o.bootstrap_since)
	const span = Date.now() - since
	return span > 0 ? Math.min(100, Math.max(0, ((Date.parse(o.bootstrap_cursor) - since) / span) * 100)) : 0
})

const statusText = computed(() => {
	const o = onboarding.value
	if (!o) return ""
	if (o.status === "pending") return "Registered. UBA starts replaying history within a minute."
	if (o.status === "live") return "UBA scores this customer's activity as it arrives."
	const replayed = o.bootstrap_cursor ? formatDate(o.bootstrap_cursor, dFormats.datetime) : "the start"
	const count = o.bootstrap_docs.toLocaleString()
	return `Learning from ${o.bootstrap_days} days of history: replayed up to ${replayed} (${count} events). Alerts start once it reaches the present.`
})

function stopPolling() {
	if (poll) {
		clearInterval(poll)
		poll = null
	}
}

function load(quiet = false) {
	if (!quiet) loading.value = true
	error.value = null
	Api.uba
		.getProvisioning(customerCode)
		.then(res => {
			info.value = res.data
			const status = res.data.onboarding?.status
			if (status === "live") {
				stopPolling()
				emit("live")
			} else if ((status === "pending" || status === "bootstrapping" || status === "error") && !poll) {
				poll = setInterval(load, POLL_MS, true)
			}
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function run() {
	running.value = true
	Api.uba
		.provision(customerCode, {
			// Registered already: keep its history setting (a live customer is never replayed again).
			bootstrap_days: registered.value ? (onboarding.value?.bootstrap_days ?? days.value) : days.value,
			deploy_wazuh_rules: deployRules.value
		})
		.then(res => {
			steps.value = res.data.steps
			message.success("UBA is set up for this customer")
			load(true)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Setting UBA up failed")
		})
		.finally(() => {
			running.value = false
		})
}

onBeforeMount(() => {
	if (isAdmin.value) load()
})
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.setup-tile {
	color: var(--primary-color);
	background-color: rgb(var(--primary-color-rgb) / 0.1);
}
</style>
