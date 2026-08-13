<template>
	<div v-if="!loading && !integrationData" class="flex min-h-80 flex-col items-center justify-center gap-4">
		<n-empty :description="emptyDescription" />
		<n-button type="primary" secondary @click="startCreate()">
			<template #icon>
				<Icon :name="AddIcon" />
			</template>
			Add Metadata
		</n-button>
	</div>
	<div v-else class="flex grow flex-col">
		<n-collapse-transition :show="mode === 'edit'">
			<CustomerIntegrationMetaForm v-if="integrationData" :integration-data @success="successHandler()">
				<template #extraActions>
					<n-button secondary @click="cancelEdit()">
						<template #icon>
							<Icon :name="BackIcon" />
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
					<CardKV v-for="(value, key) of integrationData" :key>
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
								<Icon :name="RefreshIcon" />
							</template>
							Refresh
						</n-button>
						<n-button secondary type="primary" @click="setEditMode()">
							<template #icon>
								<Icon :name="EditIcon" />
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
import type { ApiError } from "@/types/common"
import type { CustomerIntegrationMetaNetwork, CustomerIntegrationMetaThirdParty } from "@/types/integrations"
import { NButton, NCollapseTransition, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
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
const AddIcon = "carbon:add"

const message = useMessage()
const loading = ref(false)
const mode = ref<Mode>("view")
const integrationData = ref<CustomerIntegrationMetaThirdParty | CustomerIntegrationMetaNetwork | null>(null)
const emptyDescription = ref("No metadata found")
// True while the form is filling in a metadata record that does not exist yet — the state a
// deployment that failed partway leaves behind
const creating = ref(false)

function setMode(newMode: Mode): void {
	mode.value = newMode
}

function setEditMode() {
	setMode("edit")
}

function setViewMode() {
	setMode("view")
}

function startCreate() {
	// The backend picks the target table from the integration name, so an integration-shaped
	// placeholder is enough to seed the form for network connectors too
	integrationData.value = {
		id: 0,
		customer_code: customerCode,
		integration_name: integrationName
	}
	creating.value = true
	setEditMode()
}

function cancelEdit() {
	if (creating.value) {
		creating.value = false
		integrationData.value = null
	}
	setViewMode()
}

function successHandler() {
	creating.value = false
	setViewMode()
	loadMetaData()
}

function loadMetaData() {
	loading.value = true
	creating.value = false

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
			const apiError = err as ApiError
			const errorMessage = getApiErrorMessage(apiError) || "An error occurred while loading metadata"

			// A missing record is an expected state rather than a failure: report it inline and
			// let the user restore the metadata instead of only showing an error toast
			if (apiError.response?.status === 404) {
				emptyDescription.value = errorMessage
			} else {
				emptyDescription.value = "No metadata found"
				message.error(errorMessage)
			}

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
