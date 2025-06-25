<template>
	<div class="flex flex-col gap-2">
		<n-select
			v-model:value="selectedOrganization"
			:options="organizationsOptions"
			:loading="loadingList"
			:disabled="loadingList"
			placeholder="Select an Organization..."
		/>

		<n-spin v-if="selectedOrganization" :show="loadingToken" :size="14" class="app-auth-search-spinner">
			<n-el>
				<app-search-bar
					class="app-auth-search"
					:auth="organization?.org_auth.token"
					placeholder="Find an app..."
					:custom-styles="JSON.stringify({ height: '100px' })"
				></app-search-bar>
			</n-el>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { Organization } from "@/types/shuffle.d"
import { NEl, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"

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

<style lang="scss" scoped>
.app-auth-search {
	--search-input-bg: var(--input-color);
	--search-input-font-size: var(--font-size-medium);
	--search-input-border: 1px solid transparent;
	--search-input-border-radius: var(--border-radius);
	--search-input-padding: 7px 12px 6px 12px;
	--search-input-color: var(--text-color-base);
	--search-input-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0);
	--search-input-focus-border: var(--primary-color);
	--search-input-focus-shadow: 0 0 8px 0 rgba(var(--primary-color-rgb) / 0.4);
	--search-input-line-height: 1.3;
	--search-placeholder-color: var(--placeholder-color);
	--search-icon-color: var(--icon-color);
	--search-font-family: var(--font-family);
	--search-spinner-border: 1px solid transparent;
	--search-spinner-border-top: 1px solid rgba(var(--primary-color-rgb) / 0.4);
	--dropdown-bg: var(--input-color);
	--dropdown-border: 1px solid transparent;
	--dropdown-border-radius: var(--border-radius);
	--dropdown-item-border: 1px solid var(--divider-color);
	--dropdown-item-hover-bg: var(--button-color-2-hover);
	--app-icon-size: 40px;
	--app-icon-border: 1px solid var(--border-color);
	--app-icon-border-radius: var(--border-radius-small);
	--app-name-color: var(--text-color-base);
	--app-name-font-size: var(--font-size-medium);
	--empty-state-color: var(--placeholder-color);
	--empty-state-font-size: var(--font-size-medium);
}
.app-auth-search-spinner {
	:deep() {
		.n-spin-body .n-base-loading {
			position: relative;
			margin-top: 0;
			transform: translateY(-7px);
			justify-content: flex-end;
			padding-right: 16px;
		}
	}
}
</style>
