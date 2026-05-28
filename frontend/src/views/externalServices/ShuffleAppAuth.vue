<template>
	<div class="page page-wrapped page-without-footer flex flex-col gap-2 overflow-hidden">
		<n-select
			v-model:value="selectedOrganization"
			:options="organizationsOptions"
			:loading="loadingList"
			:disabled="loadingList"
			placeholder="Select an Organization..."
		/>

		<n-spin
			v-if="selectedOrganization"
			:show="loadingToken"
			class="flex grow flex-col overflow-hidden"
			content-class="h-full"
		>
			<ShuffleMCPEmbed
				v-if="organization?.org_auth?.token"
				:auth-token="organization.org_auth.token"
				placeholder="Find an app..."
				inline
				prevent-default
				class="h-full"
			/>
		</n-spin>

		<n-empty
			v-else
			description="Select an organization to manage app authentication"
			class="grow justify-center"
		/>
	</div>
</template>

<script setup lang="ts">
import type { Organization } from "@/types/shuffle.d"
import { NEmpty, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import ShuffleMCPEmbed from "@/components/shuffle/ShuffleMCPEmbed.vue"

const loadingList = ref(false)
const loadingToken = ref(false)
const message = useMessage()
const organizations = ref<Organization[]>([])
const organization = ref<Organization | null>(null)
const selectedOrganization = ref<string | null>(null)
const organizationsOptions = computed(() => organizations.value.map(o => ({ value: o.id, label: o.name })))

function getOrganizations() {
	loadingList.value = true

	Api.shuffle
		.getOrganizations()
		.then(res => {
			if (res.data.success) {
				organizations.value = res.data?.data || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingList.value = false
		})
}

function getOrganization(id: string) {
	loadingToken.value = true

	Api.shuffle
		.getOrganization(id)
		.then(res => {
			if (res.data.success) {
				organization.value = res.data?.data || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingToken.value = false
		})
}

watch(selectedOrganization, val => {
	if (val) {
		getOrganization(val)
	} else {
		organization.value = null
	}
})

onBeforeMount(() => {
	getOrganizations()
})
</script>
