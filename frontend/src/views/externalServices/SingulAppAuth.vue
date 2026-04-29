<template>
	<div class="flex flex-col gap-2">
		<n-select
			v-model:value="selectedOrganization"
			:options="organizationsOptions"
			:loading="loadingList"
			:disabled="loadingList"
			placeholder="Select an Organization..."
		/>

		<n-spin v-if="selectedOrganization" :show="loadingToken" :size="14">
			<ShuffleMCPEmbed
				v-if="organization?.org_auth?.token"
				:auth-token="organization.org_auth.token"
				placeholder="Find an app..."
				:inline="true"
			/>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { Organization } from "@/types/shuffle.d"
import { NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import ShuffleMCPEmbed from "@/components/common/ShuffleMCPEmbed.vue"

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
