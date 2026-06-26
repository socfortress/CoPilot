<template>
	<div>
		<transition name="transition-fade-move" mode="out-in">
			<div v-if="showForm" class="flex flex-col gap-4">
				<h4>{{ !!editingSource ? "Edit Event Source" : "Add Event Source" }}</h4>
				<CustomerEventSourceForm
					:customer-code
					:editing-source
					@submitted="refreshList()"
					@close="closeForm()"
				/>
			</div>
			<div v-else class="flex flex-col gap-4">
				<div class="flex items-center justify-between gap-4">
					<n-button size="small" type="primary" @click="openForm()">
						<template #icon>
							<Icon :name="AddIcon" :size="14" />
						</template>
						Add Event Source
					</n-button>
				</div>

				<n-spin :show="loading">
					<div class="min-h-52">
						<template v-if="list.length">
							<CustomerEventSourceItem
								v-for="source of list"
								:key="source.id"
								:source
								embedded
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@edit="openEdit(source)"
								@deleted="refreshList()"
							/>
						</template>
						<template v-else>
							<n-empty v-if="!loading" description="No event sources found" class="h-48 justify-center" />
						</template>
					</div>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { EventSource } from "@/types/event-sources"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerEventSourceForm from "./CustomerEventSourceForm.vue"
import CustomerEventSourceItem from "./CustomerEventSourceItem.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const AddIcon = "carbon:add-alt"

const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const list = ref<EventSource[]>([])
const editingSource = ref<EventSource | null>(null)

function getEventSources() {
	loading.value = true

	Api.siem
		.getEventSources(customerCode)
		.then(res => {
			if (res.data.success) {
				list.value = res.data?.event_sources || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function openForm() {
	editingSource.value = null
	showForm.value = true
}

function openEdit(source: EventSource) {
	editingSource.value = source
	showForm.value = true
}

function closeForm() {
	editingSource.value = null
	showForm.value = false
}

function refreshList() {
	closeForm()
	getEventSources()
}

onBeforeMount(() => {
	getEventSources()
})
</script>
