<template>
	<div class="@container flex flex-col gap-4">
		<n-alert type="info">
			SCA Policies provides CIS benchmark policies for Security Configuration Assessment using
			<a
				href="https://documentation.wazuh.com/current/user-manual/capabilities/sec-config-assessment/index.html"
				target="_blank"
			>
				Wazuh Security Configuration Assessment (SCA)
			</a>
			. Deploy policy
			<code>.yml</code>
			files to your endpoints under
			<code>/var/ossec/ruleset/sca/</code>
			, set ownership, and restart the Wazuh agent. See
			<a href="https://github.com/socfortress/CoPilot-SCA" target="_blank">CoPilot-SCA</a>
			for available policies.
		</n-alert>

		<div class="flex flex-col">
			<ListToolbar
				v-model:search-query="searchQuery"
				v-model:selected-platform="selectedPlatform"
				v-model:selected-application="selectedApplication"
				:platform-options
				:application-options
				@reset-filters="resetFilters"
			>
				<template #info>
					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<div class="bg-default rounded-lg">
								<n-button size="small" class="cursor-help!">
									<template #icon>
										<Icon :name="InfoIcon" />
									</template>
								</n-button>
							</div>
						</template>
						<div class="flex flex-col gap-2">
							<div class="box">
								Total Policies:
								<code>{{ policies.length }}</code>
							</div>
							<div class="box">
								Filtered:
								<code>{{ filteredPolicies.length }}</code>
							</div>
						</div>
					</n-popover>
				</template>
			</ListToolbar>

			<n-spin :show="loading">
				<div class="my-3">
					<div
						v-if="paginatedPolicies.length"
						class="grid grid-cols-1 gap-4 @2xl:grid-cols-2 @5xl:grid-cols-3 @6xl:grid-cols-4"
					>
						<PolicyCard v-for="policy of paginatedPolicies" :key="policy.id" :policy />
					</div>

					<template v-else>
						<n-empty v-if="!loading" description="No policies found" class="h-48 justify-center" />
					</template>
				</div>
			</n-spin>

			<div class="flex justify-end">
				<n-pagination
					v-if="filteredPolicies.length > pageSize"
					v-model:page="currentPage"
					:page-size
					:item-count="filteredPolicies.length"
					:page-slot="6"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ScaPolicyItem } from "@/types/sca.d"
import { NAlert, NButton, NEmpty, NPagination, NPopover, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ListToolbar from "./ListToolbar.vue"
import PolicyCard from "./PolicyCard.vue"

const loading = ref(false)
const message = useMessage()
const policies = ref<ScaPolicyItem[]>([])

const searchQuery = ref<string | null>(null)
const selectedPlatform = ref<string | null>(null)
const selectedApplication = ref<string | null>(null)
const currentPage = ref(1)
const pageSize = 24

const InfoIcon = "carbon:information"

const platformOptions = computed(() => {
	const platforms = [...new Set(policies.value.map(p => p.platform))].sort()
	return platforms.map(p => ({ label: p, value: p }))
})

const applicationOptions = computed(() => {
	const apps = [...new Set(policies.value.map(p => p.application))].sort()
	return apps.map(a => ({ label: a, value: a }))
})

const filteredPolicies = computed(() => {
	let result = policies.value

	if (searchQuery.value) {
		const q = searchQuery.value.toLowerCase()
		result = result.filter(
			p =>
				p.name.toLowerCase().includes(q) ||
				p.description.toLowerCase().includes(q) ||
				p.application.toLowerCase().includes(q) ||
				p.id.toLowerCase().includes(q)
		)
	}

	if (selectedPlatform.value) {
		result = result.filter(p => p.platform === selectedPlatform.value)
	}

	if (selectedApplication.value) {
		result = result.filter(p => p.application === selectedApplication.value)
	}

	return result
})

const paginatedPolicies = computed(() => {
	const start = (currentPage.value - 1) * pageSize
	return filteredPolicies.value.slice(start, start + pageSize)
})

function resetFilters() {
	selectedPlatform.value = null
	selectedApplication.value = null
}

async function loadPolicies() {
	loading.value = true
	try {
		const res = await Api.sca.getPolicies()
		if (res.data.success) {
			policies.value = res.data.policies || []
		} else {
			message.warning(res.data?.message || "Failed to load SCA policies")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load SCA policies")
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadPolicies()
})
</script>
