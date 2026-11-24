<template>
	<div class="flex flex-col gap-4" data-testid="cloud-assessment-page">
		<header class="mt-4 flex flex-wrap items-end justify-between gap-4">
			<div class="flex min-w-0 grow basis-96 flex-col gap-1.5">
				<h2 class="m-0 text-xl leading-none font-semibold">Cloud Security Assessment</h2>
				<p class="text-secondary m-0 max-w-2xl text-sm">
					Prowler scans of customers' AWS, Azure, Google Cloud and Microsoft 365 accounts: what failed, what's new
					since the last scan, and how each scan maps onto compliance frameworks.
				</p>
			</div>
			<div class="text-tertiary flex shrink-0 items-center gap-2 font-mono text-xs" data-testid="cloud-runner-version">
				<template v-if="availability?.prowler_version">Prowler {{ availability.prowler_version }}</template>
			</div>
		</header>

		<n-alert v-if="runnerProblem" type="warning" :bordered="false" data-testid="cloud-runner-problem">
			{{ runnerProblem }} Scans stay queued until copilot-prowler answers.
		</n-alert>

		<CloudAccountDetail
			v-if="accountId !== null && customerCode"
			:key="`${customerCode}:${accountId}`"
			:customer-code
			:account-id
			@back="showOverview"
		/>
		<CloudAccountsOverview v-else @open="openAccount" />
	</div>
</template>

<script setup lang="ts">
import type { CloudAccount } from "@/types/cloud-assessment"
import { NAlert } from "naive-ui"
import { computed, onBeforeMount } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useRouteQueryParam } from "@/composables/useNavigation"
import CloudAccountDetail from "./CloudAccountDetail.vue"
import CloudAccountsOverview from "./CloudAccountsOverview.vue"
import { useCloudAvailability } from "./useCloudAvailability"

const route = useRoute()
const router = useRouter()
const { availability, load } = useCloudAvailability()

// The customer and account (and, below, the scan and tab) live in the URL, so a view can be
// linked and survives a reload. Opening an account is a new place: push. Leaving it: push too,
// so browser back returns to the account.
const customerQuery = useRouteQueryParam("customer")
const accountQuery = useRouteQueryParam("account")

const customerCode = computed(() => customerQuery.value ?? null)
const accountId = computed(() => {
	const value = Number(accountQuery.value)
	return Number.isInteger(value) && value > 0 ? value : null
})

const runnerProblem = computed(() => {
	const current = availability.value
	if (!current) return null
	if (!current.runner_configured || !current.runner_reachable) return current.runner_problem
	return null
})

function openAccount(account: CloudAccount) {
	router.push({ query: { customer: account.customer_code, account: String(account.id) } })
}

/** The query keys an account's view owns: leaving the account drops them all. */
const ACCOUNT_KEYS = ["customer", "account", "scan", "tab", "framework", "check"]

function showOverview() {
	const query = { ...route.query }
	for (const key of ACCOUNT_KEYS) delete query[key]
	router.push({ query })
}

onBeforeMount(() => {
	void load()
})
</script>
