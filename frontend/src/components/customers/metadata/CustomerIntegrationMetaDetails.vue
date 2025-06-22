<template>
	<div v-if="!loading && !integrationData" class="flex min-h-80 items-center justify-center">
		<n-empty description="No metadata found" />
	</div>
	<div v-else class="flex grow flex-col">
		<n-collapse-transition :show="mode === 'edit'">
			<CustomerIntegrationMetaForm v-if="integrationData" :integration-data @success="successHandler()">
				<template #extraActions>
					<n-button secondary @click="setViewMode()">
						<template #icon>
							<Icon :name="BackIcon"></Icon>
						</template>
						Back
					</n-button>
				</template>
			</CustomerIntegrationMetaForm>
		</n-collapse-transition>
		<n-collapse-transition :show="mode === 'view'" class="flex grow flex-col">
			<n-spin
				:show="loading"
				content-class="flex grow flex-col justify-between gap-14"
				class="flex grow flex-col"
			>
				<!-- Read-only View (when not editing) -->
				<div class="grid-auto-fit-200 grid gap-2">
					<CardKV v-for="(value, key) of integrationData" :key="key">
						<template #key>
							{{ getMetaFieldLabel(`${key}`) }}
						</template>
						<template #value>
							{{ value || "—" }}
						</template>
					</CardKV>
				</div>

				<!-- Bottom Actions -->
				<div class="flex items-center justify-end">
					<div class="flex gap-3">
						<n-button secondary :loading @click="loadMetaData()">
							<template #icon>
								<Icon :name="RefreshIcon"></Icon>
							</template>
							Refresh
						</n-button>
						<n-button secondary type="primary" @click="setEditMode()">
							<template #icon>
								<Icon :name="EditIcon"></Icon>
							</template>
							Edit
						</n-button>
					</div>
				</div>
			</n-spin>
		</n-collapse-transition>
	</div>
</template>

<script setup lang="ts">
import type { CustomerIntegrationMetaNetwork, CustomerIntegrationMetaThirdParty } from "@/types/integrations.d"
import { NButton, NCollapseTransition, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import CustomerIntegrationMetaForm from "./CustomerIntegrationMetaForm.vue"
import { getMetaFieldLabel } from "./utils"

const { customerCode, integrationName } = defineProps<{
	customerCode: string
	integrationName: string
}>()

type Mode = "view" | "edit"

const RefreshIcon = "carbon:renew"
const EditIcon = "carbon:edit"
const BackIcon = "carbon:arrow-left"

const message = useMessage()
const loading = ref(false)
const mode = ref<Mode>("view")
const integrationData = ref<CustomerIntegrationMetaThirdParty | CustomerIntegrationMetaNetwork | null>(null)

function setMode(newMode: Mode): void {
	mode.value = newMode
}

function setEditMode() {
	setMode("edit")
}

function setViewMode() {
	setMode("view")
}

function successHandler() {
	setViewMode()
	loadMetaData()
}

function loadMetaData() {
	loading.value = true

	Api.integrations
		.getMetaAuto(customerCode, integrationName)
		.then(res => {
			if (res.data.success) {
				integrationData.value = res.data.data
			} else {
				message.warning(res.data?.message || "Failed to load metadata")
				integrationData.value = null
			}
		})
		.catch(err => {
			const errorMsg = err.response?.data?.message || "An error occurred while loading metadata"
			message.error(errorMsg)
			integrationData.value = null
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	loadMetaData()
})
</script>
